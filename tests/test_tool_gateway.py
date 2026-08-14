from __future__ import annotations

import threading
import time
from typing import Literal

import pytest
from pydantic import ValidationError

from deep_research_agent.kernel.contracts import TaskSpec
from deep_research_agent.tool_gateway.gateway import ToolGateway
from deep_research_agent.tool_gateway.models import (
    ToolExecutionContext,
    ToolInvocation,
    ToolResultEnvelope,
    ToolSpec,
)
from deep_research_agent.tool_gateway.registry import (
    InMemoryArtifactStore,
    InMemoryBudgetStore,
    InMemoryToolRegistry,
    ToolCache,
)


def _task(
    *,
    role: str = "researcher",
    max_tool_calls: int = 3,
    job_id: str = "job-1",
) -> TaskSpec:
    return TaskSpec(
        task_id="task-1",
        job_id=job_id,
        kind="collect",
        role=role,
        objective="Collect evidence.",
        output_schema={"type": "object"},
        budget={"max_tool_calls": max_tool_calls},
        idempotency_key=f"{job_id}:task-1",
    )


def _context(
    *,
    tenant_id: str = "tenant-a",
    role: str = "researcher",
    job_id: str = "job-1",
) -> ToolExecutionContext:
    return ToolExecutionContext(
        tenant_id=tenant_id,
        role=role,
        job_id=job_id,
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
    cache: ToolCache | None = None,
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
            retry_safety="read_only",
            cache_scope="job",
            cache_ttl_seconds=60,
        ),
        handler,
    )
    return ToolGateway(
        registry=registry,
        artifact_store=artifact_store,
        budget_store=budget_store,
        cache=cache,
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


def test_empty_tenant_allowlist_is_rejected_by_default() -> None:
    with pytest.raises(ValidationError, match="tenant allowlist"):
        ToolSpec(name="search", allowed_roles=("researcher",))


def test_authenticated_tenant_scope_must_be_explicit() -> None:
    gateway = _gateway(
        lambda arguments, _tool_context: arguments,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            tenant_scope="authenticated",
        ),
    )

    result = gateway.invoke(
        _task(),
        _call(tenant_id="tenant-b"),
        _context(tenant_id="tenant-b"),
    )

    assert result.status == "succeeded"


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


def test_cached_artifact_references_are_isolated_by_job() -> None:
    calls = 0
    artifact_store = InMemoryArtifactStore()

    def handler(_arguments: dict[str, object], tool_context) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"content": "x" * 200, "job_id": tool_context.job_id}

    gateway = _gateway(
        handler,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            retry_safety="read_only",
            cache_scope="job",
            cache_ttl_seconds=60,
            max_inline_result_bytes=32,
        ),
        artifact_store=artifact_store,
    )

    first = gateway.invoke(_task(job_id="job-1"), _call(), _context(job_id="job-1"))
    second = gateway.invoke(
        _task(job_id="job-2"),
        _call(idempotency_key="call-2"),
        _context(job_id="job-2"),
    )

    assert first.artifact is not None
    assert second.artifact is not None
    assert first.artifact.metadata["job_id"] == "job-1"
    assert second.artifact.metadata["job_id"] == "job-2"
    assert first.artifact.artifact_id != second.artifact.artifact_id
    assert second.from_cache is False
    assert calls == 2


def test_cache_get_failure_is_retryable_and_does_not_stick_idempotency() -> None:
    calls = 0

    class FailingGetCache:
        def get(self, _key: str) -> ToolResultEnvelope | None:
            raise RuntimeError("cache unavailable")

        def put(
            self,
            _key: str,
            _value: ToolResultEnvelope,
            _ttl_seconds: float,
        ) -> None:
            raise AssertionError("cache put must not run")

    def handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    gateway = _gateway(handler, cache=FailingGetCache())

    result = gateway.invoke(_task(), _call(), _context())
    duplicate = gateway.invoke(_task(), _call(), _context())

    assert result.status == "failed"
    assert result.error_code == "cache_backend_error"
    assert result.attempt_count == 0
    assert duplicate.status == "failed"
    assert duplicate.duplicate is False
    assert calls == 0


def test_cache_put_failure_does_not_strand_completed_idempotency() -> None:
    calls = 0

    class FailingPutCache:
        def get(self, _key: str) -> ToolResultEnvelope | None:
            return None

        def put(
            self,
            _key: str,
            _value: ToolResultEnvelope,
            _ttl_seconds: float,
        ) -> None:
            raise RuntimeError("cache unavailable")

    def handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    gateway = _gateway(handler, cache=FailingPutCache())

    result = gateway.invoke(_task(), _call(), _context())
    duplicate = gateway.invoke(_task(), _call(), _context())

    assert result.status == "succeeded"
    assert duplicate.status == "succeeded"
    assert duplicate.duplicate is True
    assert calls == 1


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
            retry_safety="read_only",
            cache_ttl_seconds=0,
        ),
    )

    result = gateway.invoke(_task(), _call(), _context())

    assert result.status == "succeeded"
    assert result.attempt_count == 3
    assert calls == 3
    assert observed_idempotency_keys == ["call-1", "call-1", "call-1"]


def test_retry_requires_explicit_safe_tool_semantics() -> None:
    with pytest.raises(ValidationError, match="retry-safe"):
        ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            max_retries=1,
        )


@pytest.mark.parametrize("unsafe_retry_safety", ["never", "adapter_idempotent"])
def test_cache_requires_explicit_job_scoped_read_only_policy(
    unsafe_retry_safety: Literal["never", "adapter_idempotent"],
) -> None:
    spec = ToolSpec(
        name="search",
        allowed_roles=("researcher",),
        allowed_tenant_ids=("tenant-a",),
        retry_safety="read_only",
        cache_scope="job",
        cache_ttl_seconds=60,
    )

    assert spec.cache_scope == "job"

    with pytest.raises(ValidationError, match="job cache scope"):
        ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            retry_safety="read_only",
            cache_ttl_seconds=60,
        )

    with pytest.raises(ValidationError, match="read-only"):
        ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            retry_safety=unsafe_retry_safety,
            cache_scope="job",
            cache_ttl_seconds=60,
        )


@pytest.mark.parametrize(
    "invalid_arguments",
    [
        {"value": object()},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": float("-inf")},
    ],
)
def test_invocation_arguments_reject_non_finite_json_before_invoke(
    invalid_arguments: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _call(arguments=invalid_arguments)


def test_invocation_arguments_reject_cycles_before_invoke() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic

    with pytest.raises(ValidationError):
        _call(arguments=cyclic)


def test_timeout_stays_pending_and_never_starts_a_retry() -> None:
    started = threading.Event()
    release = threading.Event()
    calls = 0

    def slow_handler(_arguments: dict[str, object], _tool_context: object) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        started.set()
        release.wait(timeout=1.0)
        return {"ok": True}

    gateway = _gateway(
        slow_handler,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.01,
            max_retries=2,
            retry_safety="read_only",
            cache_ttl_seconds=0,
        ),
    )

    result = gateway.invoke(_task(), _call(), _context())
    duplicate_while_running = gateway.invoke(_task(), _call(), _context())

    assert started.is_set()
    assert result.status == "execution_uncertain"
    assert result.error_code == "execution_uncertain"
    assert result.trust == "untrusted"
    assert result.attempt_count == 1
    assert duplicate_while_running.status == "denied"
    assert duplicate_while_running.error_code == "idempotency_in_progress"
    assert calls == 1

    release.set()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        duplicate_after_completion = gateway.invoke(_task(), _call(), _context())
        if duplicate_after_completion.status == "succeeded":
            break
        time.sleep(0.005)
    else:
        pytest.fail("timed-out handler did not finalize its idempotency record")

    assert duplicate_after_completion.duplicate is True
    assert duplicate_after_completion.output == {"ok": True}
    assert calls == 1


def test_delayed_timeout_completion_survives_cache_put_failure() -> None:
    release = threading.Event()
    calls = 0

    class FailingPutCache:
        def get(self, _key: str) -> ToolResultEnvelope | None:
            return None

        def put(
            self,
            _key: str,
            _value: ToolResultEnvelope,
            _ttl_seconds: float,
        ) -> None:
            raise RuntimeError("cache unavailable")

    def slow_handler(
        _arguments: dict[str, object],
        _tool_context: object,
    ) -> dict[str, bool]:
        nonlocal calls
        calls += 1
        release.wait(timeout=1.0)
        return {"ok": True}

    gateway = _gateway(
        slow_handler,
        spec=ToolSpec(
            name="search",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-a",),
            timeout_seconds=0.01,
            retry_safety="read_only",
            cache_scope="job",
            cache_ttl_seconds=60,
        ),
        cache=FailingPutCache(),
    )

    result = gateway.invoke(_task(), _call(), _context())
    assert result.status == "execution_uncertain"

    release.set()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        duplicate = gateway.invoke(_task(), _call(), _context())
        if duplicate.status == "succeeded":
            break
        time.sleep(0.005)
    else:
        pytest.fail("cache put failure stranded delayed idempotency completion")

    assert duplicate.duplicate is True
    assert duplicate.output == {"ok": True}
    assert calls == 1


@pytest.mark.parametrize("invalid_output", [object(), float("nan")])
def test_non_json_tool_output_fails_and_retries_freshly(invalid_output: object) -> None:
    calls = 0

    def handler(_arguments: dict[str, object], _tool_context: object) -> object:
        nonlocal calls
        calls += 1
        return invalid_output

    gateway = _gateway(handler)

    result = gateway.invoke(_task(), _call(), _context())
    duplicate = gateway.invoke(_task(), _call(), _context())

    assert result.status == "failed"
    assert result.error_code == "invalid_tool_result"
    assert duplicate.status == "failed"
    assert duplicate.duplicate is False
    assert calls == 2


def test_cyclic_tool_output_fails_and_is_retryable() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    gateway = _gateway(lambda _arguments, _tool_context: cyclic)

    result = gateway.invoke(_task(), _call(), _context())
    duplicate = gateway.invoke(_task(), _call(), _context())

    assert result.status == "failed"
    assert result.error_code == "invalid_tool_result"
    assert duplicate.status == "failed"
    assert duplicate.duplicate is False


def test_result_envelope_rejects_non_json_inline_output() -> None:
    with pytest.raises(ValidationError):
        ToolResultEnvelope(
            invocation_id="invocation-1",
            tool_name="search",
            tenant_id="tenant-a",
            status="succeeded",
            output=object(),
        )


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
    assert result.artifact.metadata["tenant_id"] == "tenant-a"
    assert result.artifact.metadata["job_id"] == "job-1"
    assert artifact_store.read(
        result.artifact.artifact_id,
        tenant_id="tenant-a",
        job_id="job-1",
    ) == b'{"content":"' + b"x" * 200 + b'"}'
    with pytest.raises(PermissionError):
        artifact_store.read(
            result.artifact.artifact_id,
            tenant_id="tenant-b",
            job_id="job-1",
        )
    with pytest.raises(PermissionError):
        artifact_store.read(
            result.artifact.artifact_id,
            tenant_id="tenant-a",
            job_id="job-2",
        )


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
