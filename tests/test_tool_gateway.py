from __future__ import annotations

import time

import pytest

from deep_research_agent.kernel.contracts import TaskSpec
from deep_research_agent.tool_gateway.gateway import ToolGateway
from deep_research_agent.tool_gateway.models import (
    ToolExecutionContext,
    ToolInvocation,
    ToolSpec,
)
from deep_research_agent.tool_gateway.registry import (
    InMemoryArtifactStore,
    InMemoryBudgetStore,
    InMemoryToolRegistry,
)


def _task(*, role: str = "researcher", max_tool_calls: int = 3) -> TaskSpec:
    return TaskSpec(
        task_id="task-1",
        job_id="job-1",
        kind="collect",
        role=role,
        objective="Collect evidence.",
        output_schema={"type": "object"},
        budget={"max_tool_calls": max_tool_calls},
        idempotency_key="job-1:task-1",
    )


def _context(*, tenant_id: str = "tenant-a", role: str = "researcher") -> ToolExecutionContext:
    return ToolExecutionContext(
        tenant_id=tenant_id,
        role=role,
        job_id="job-1",
    )


def _call(
    *,
    tool_name: str = "search",
    tenant_id: str = "tenant-a",
    idempotency_key: str = "call-1",
    arguments: dict[str, object] | None = None,
) -> ToolInvocation:
    return ToolInvocation(
        invocation_id=f"invocation:{idempotency_key}",
        tool_name=tool_name,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        arguments=arguments or {"query": "evidence"},
    )


def _gateway(
    handler,
    *,
    spec: ToolSpec | None = None,
    artifact_store: InMemoryArtifactStore | None = None,
    budget_store: InMemoryBudgetStore | None = None,
) -> ToolGateway:
    registry = InMemoryToolRegistry()
    registry.register(
        spec
        or ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.5,
            max_retries=0,
            cache_ttl_seconds=60,
        ),
        handler,
    )
    return ToolGateway(
        registry=registry,
        artifact_store=artifact_store,
        budget_store=budget_store,
    )


def test_gateway_denies_role_without_running_tool() -> None:
    calls = 0

    def handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    gateway = _gateway(handler)
    result = gateway.invoke(_task(role="planner"), _call(), _context(role="planner"))

    assert result.status == "denied"
    assert result.error_code == "role_not_allowed"
    assert result.trust == "untrusted"
    assert calls == 0


def test_gateway_denies_cross_tenant_invocation_without_running_tool() -> None:
    calls = 0

    def handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    gateway = _gateway(handler)
    result = gateway.invoke(_task(), _call(tenant_id="tenant-b"), _context())

    assert result.status == "denied"
    assert result.error_code == "tenant_mismatch"
    assert calls == 0


def test_cache_hit_is_tenant_scoped_and_does_not_consume_a_second_budget_unit() -> None:
    calls = 0
    budget_store = InMemoryBudgetStore()

    def handler(arguments: dict[str, object], _tool_context: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"answer": arguments["query"]}

    gateway = _gateway(handler, budget_store=budget_store)
    first = gateway.invoke(_task(max_tool_calls=1), _call(), _context())
    second = gateway.invoke(
        _task(max_tool_calls=1),
        _call(idempotency_key="call-2"),
        _context(),
    )

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert second.from_cache is True
    assert second.output == {"answer": "evidence"}
    assert calls == 1
    assert budget_store.used("tenant-a", "job-1", "task-1") == 1


def test_duplicate_idempotency_key_returns_recorded_envelope_once() -> None:
    calls = 0

    def handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    gateway = _gateway(handler)
    first = gateway.invoke(_task(), _call(), _context())
    duplicate = gateway.invoke(_task(), _call(), _context())

    assert first.status == "succeeded"
    assert duplicate.status == "succeeded"
    assert duplicate.duplicate is True
    assert duplicate.output == {"calls": 1}
    assert calls == 1


def test_reusing_idempotency_key_for_different_arguments_is_denied() -> None:
    gateway = _gateway(lambda arguments, _tool_context: arguments)
    gateway.invoke(_task(), _call(), _context())

    conflict = gateway.invoke(
        _task(),
        _call(arguments={"query": "different"}),
        _context(),
    )

    assert conflict.status == "denied"
    assert conflict.error_code == "idempotency_conflict"


def test_budget_is_enforced_before_a_second_uncached_execution() -> None:
    calls = 0

    def handler(arguments: dict[str, object], _tool_context: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return arguments

    gateway = _gateway(handler)
    gateway.invoke(_task(max_tool_calls=1), _call(), _context())
    denied = gateway.invoke(
        _task(max_tool_calls=1),
        _call(idempotency_key="call-2", arguments={"query": "new"}),
        _context(),
    )

    assert denied.status == "denied"
    assert denied.error_code == "budget_exhausted"
    assert calls == 1


def test_retry_policy_is_bounded_and_records_actual_attempt_count() -> None:
    calls = 0

    observed_idempotency_keys: list[str] = []

    def flaky_handler(_arguments: dict[str, object], tool_context) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        observed_idempotency_keys.append(tool_context.idempotency_key)
        if calls < 3:
            raise ConnectionError("temporary failure")
        return {"ok": True}

    gateway = _gateway(
        flaky_handler,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.5,
            max_retries=2,
            cache_ttl_seconds=0,
        ),
    )

    result = gateway.invoke(_task(), _call(), _context())

    assert result.status == "succeeded"
    assert result.attempt_count == 3
    assert calls == 3
    assert observed_idempotency_keys == ["call-1", "call-1", "call-1"]


def test_timeout_is_returned_as_untrusted_failure_envelope() -> None:
    def slow_handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        time.sleep(0.05)
        return {"ok": True}

    gateway = _gateway(
        slow_handler,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.005,
            max_retries=0,
            cache_ttl_seconds=0,
        ),
    )

    result = gateway.invoke(_task(), _call(), _context())

    assert result.status == "failed"
    assert result.error_code == "timeout"
    assert result.trust == "untrusted"
    assert result.attempt_count == 1


def test_large_tool_output_is_stored_as_an_artifact_reference() -> None:
    artifact_store = InMemoryArtifactStore()
    gateway = _gateway(
        lambda _arguments, _tool_context: {"content": "x" * 200},
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.5,
            max_retries=0,
            cache_ttl_seconds=0,
            max_inline_result_bytes=32,
        ),
        artifact_store=artifact_store,
    )

    result = gateway.invoke(_task(), _call(), _context())

    assert result.status == "succeeded"
    assert result.output is None
    assert result.artifact is not None
    assert result.artifact.media_type == "application/json"
    assert result.artifact.created_by_task_id == "task-1"
    assert artifact_store.read(result.artifact.artifact_id) == b'{"content":"' + b"x" * 200 + b'"}'


def test_unknown_tool_is_denied_without_consuming_budget() -> None:
    budget_store = InMemoryBudgetStore()
    gateway = _gateway(
        lambda arguments, _tool_context: arguments,
        budget_store=budget_store,
    )

    result = gateway.invoke(_task(), _call(tool_name="filesystem"), _context())

    assert result.status == "denied"
    assert result.error_code == "tool_not_allowed"
    assert budget_store.used("tenant-a", "job-1", "task-1") == 0


def test_context_must_match_task_job_and_role() -> None:
    gateway = _gateway(lambda arguments, _tool_context: arguments)

    with pytest.raises(ValueError, match="context role"):
        gateway.invoke(_task(), _call(), _context(role="planner"))

    mismatched_job = _context().model_copy(update={"job_id": "job-2"})
    with pytest.raises(ValueError, match="context job"):
        gateway.invoke(_task(), _call(idempotency_key="call-2"), mismatched_job)
