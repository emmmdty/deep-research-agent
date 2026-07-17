"""Policy-enforcing execution gateway for untrusted tool calls."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from typing import Any

from deep_research_agent.kernel.contracts import TaskSpec
from deep_research_agent.tool_gateway.models import (
    ToolExecutionContext,
    ToolHandlerContext,
    ToolInvocation,
    ToolResultEnvelope,
)
from deep_research_agent.tool_gateway.registry import (
    ArtifactStore,
    BudgetStore,
    IdempotencyStore,
    InMemoryArtifactStore,
    InMemoryBudgetStore,
    InMemoryIdempotencyStore,
    InMemoryToolCache,
    ToolCache,
    ToolRegistry,
)


class ToolGateway:
    """Fail-closed tool gateway owned by the deterministic harness."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        cache: ToolCache | None = None,
        idempotency_store: IdempotencyStore | None = None,
        budget_store: BudgetStore | None = None,
        artifact_store: ArtifactStore | None = None,
        executor: concurrent.futures.Executor | None = None,
    ) -> None:
        self._registry = registry
        self._cache = cache if cache is not None else InMemoryToolCache()
        self._idempotency = (
            idempotency_store if idempotency_store is not None else InMemoryIdempotencyStore()
        )
        self._budget = budget_store if budget_store is not None else InMemoryBudgetStore()
        self._artifacts = artifact_store if artifact_store is not None else InMemoryArtifactStore()
        self._executor = executor or concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def invoke(
        self,
        task: TaskSpec,
        call: ToolInvocation,
        context: ToolExecutionContext,
    ) -> ToolResultEnvelope:
        self._validate_context(task, context)
        registered = self._registry.get(call.tool_name)
        if registered is None:
            return self._denied(call, "tool_not_allowed", "tool is not registered")
        spec = registered.spec
        if task.role not in spec.allowed_roles:
            return self._denied(call, "role_not_allowed", "task role cannot invoke this tool")
        if call.tenant_id != context.tenant_id:
            return self._denied(call, "tenant_mismatch", "call tenant differs from context")
        if spec.allowed_tenant_ids and context.tenant_id not in spec.allowed_tenant_ids:
            return self._denied(call, "tenant_not_allowed", "tenant cannot invoke this tool")

        fingerprint = self._fingerprint(task, call, context)
        idempotency_scope = f"{context.tenant_id}:{context.job_id}"
        state = self._idempotency.begin(
            idempotency_scope,
            call.idempotency_key,
            fingerprint,
        )
        if state == "conflict":
            return self._denied(
                call,
                "idempotency_conflict",
                "idempotency key was already used for a different invocation",
            )
        if state == "pending":
            return self._denied(
                call,
                "idempotency_in_progress",
                "an invocation with this idempotency key is in progress",
            )
        if state == "duplicate":
            previous = self._idempotency.get(idempotency_scope, call.idempotency_key)
            if previous is None:
                raise RuntimeError("completed idempotency record has no result")
            return previous.model_copy(update={"duplicate": True})

        cache_key = self._cache_key(call, context)
        if spec.cache_ttl_seconds > 0:
            cached = self._cache.get(cache_key)
            if cached is not None:
                result = cached.model_copy(
                    update={
                        "invocation_id": call.invocation_id,
                        "tenant_id": call.tenant_id,
                        "from_cache": True,
                        "duplicate": False,
                    }
                )
                self._complete_idempotency(
                    idempotency_scope,
                    call,
                    fingerprint,
                    result,
                )
                return result

        max_tool_calls = int(task.budget.get("max_tool_calls", 0))
        if max_tool_calls <= 0 or not self._budget.consume(
            context.tenant_id,
            context.job_id,
            task.task_id,
            max_tool_calls,
        ):
            result = self._denied(call, "budget_exhausted", "task tool-call budget is exhausted")
            self._complete_idempotency(
                idempotency_scope,
                call,
                fingerprint,
                result,
            )
            return result

        result = self._execute(
            task,
            call,
            context,
            registered.handler,
            spec.timeout_seconds,
            spec.max_retries,
        )
        if result.status == "succeeded" and spec.cache_ttl_seconds > 0:
            self._cache.put(cache_key, result, spec.cache_ttl_seconds)
        self._complete_idempotency(
            idempotency_scope,
            call,
            fingerprint,
            result,
        )
        return result

    def _execute(
        self,
        task: TaskSpec,
        call: ToolInvocation,
        context: ToolExecutionContext,
        handler,
        timeout_seconds: float,
        max_retries: int,
    ) -> ToolResultEnvelope:
        handler_context = ToolHandlerContext(
            invocation_id=call.invocation_id,
            idempotency_key=call.idempotency_key,
            tenant_id=context.tenant_id,
            role=context.role,
            job_id=context.job_id,
            task_id=task.task_id,
        )
        for attempt_index in range(max_retries + 1):
            future = self._executor.submit(handler, dict(call.arguments), handler_context)
            try:
                output = future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                future.cancel()
                if attempt_index < max_retries:
                    continue
                return self._failed(
                    call,
                    "timeout",
                    "tool execution exceeded its timeout",
                    attempt_index + 1,
                )
            except Exception as exc:
                if attempt_index < max_retries:
                    continue
                return self._failed(
                    call,
                    "tool_error",
                    str(exc) or type(exc).__name__,
                    attempt_index + 1,
                )

            serialized = json.dumps(
                output,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
                default=str,
            ).encode("utf-8")
            registered = self._registry.get(call.tool_name)
            if registered is None:
                raise RuntimeError("tool registration disappeared during execution")
            if len(serialized) > registered.spec.max_inline_result_bytes:
                artifact = self._artifacts.write(
                    serialized,
                    media_type="application/json",
                    task_id=task.task_id,
                )
                return ToolResultEnvelope(
                    invocation_id=call.invocation_id,
                    tool_name=call.tool_name,
                    tenant_id=call.tenant_id,
                    status="succeeded",
                    artifact=artifact,
                    attempt_count=attempt_index + 1,
                )
            return ToolResultEnvelope(
                invocation_id=call.invocation_id,
                tool_name=call.tool_name,
                tenant_id=call.tenant_id,
                status="succeeded",
                output=output,
                attempt_count=attempt_index + 1,
            )
        raise RuntimeError("unreachable tool execution state")

    def _complete_idempotency(
        self,
        scope: str,
        call: ToolInvocation,
        fingerprint: str,
        result: ToolResultEnvelope,
    ) -> None:
        self._idempotency.complete(scope, call.idempotency_key, fingerprint, result)

    @staticmethod
    def _validate_context(task: TaskSpec, context: ToolExecutionContext) -> None:
        if task.role != context.role:
            raise ValueError("context role must match task role")
        if task.job_id != context.job_id:
            raise ValueError("context job must match task job")

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        )

    @classmethod
    def _fingerprint(
        cls,
        task: TaskSpec,
        call: ToolInvocation,
        context: ToolExecutionContext,
    ) -> str:
        payload = {
            "arguments": call.arguments,
            "job_id": context.job_id,
            "role": context.role,
            "task_id": task.task_id,
            "tenant_id": context.tenant_id,
            "tool_name": call.tool_name,
        }
        return hashlib.sha256(cls._canonical_json(payload).encode("utf-8")).hexdigest()

    @classmethod
    def _cache_key(cls, call: ToolInvocation, context: ToolExecutionContext) -> str:
        payload = {
            "arguments": call.arguments,
            "role": context.role,
            "tenant_id": context.tenant_id,
            "tool_name": call.tool_name,
        }
        return hashlib.sha256(cls._canonical_json(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def _denied(call: ToolInvocation, code: str, error: str) -> ToolResultEnvelope:
        return ToolResultEnvelope(
            invocation_id=call.invocation_id,
            tool_name=call.tool_name,
            tenant_id=call.tenant_id,
            status="denied",
            error_code=code,
            error=error,
        )

    @staticmethod
    def _failed(
        call: ToolInvocation,
        code: str,
        error: str,
        attempt_count: int,
    ) -> ToolResultEnvelope:
        return ToolResultEnvelope(
            invocation_id=call.invocation_id,
            tool_name=call.tool_name,
            tenant_id=call.tenant_id,
            status="failed",
            error_code=code,
            error=error,
            attempt_count=attempt_count,
        )
