"""Phase 3 observability wiring: per-job cost attribution, span wrapping, /metrics.

Covers contract T11: contextvar attribution, whitelisted research spans on
LLM/tool calls, the /metrics Prometheus endpoint with a deterministic fallback,
offline no-op tracing, and cost metrics persisted into the scheduler bundle.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from deep_research_agent.observability.cost_tracker import (
    CostTracker,
    current_job_id,
    get_tracker,
    reset_job_id,
    set_job_id,
)


class FakeSpan:
    """In-memory span that mimics the tracing surface used by research_span."""

    def __init__(self, name: str, attributes: dict) -> None:
        self.name = name
        self.attributes = dict(attributes)
        self.set_attributes: list[tuple[str, object]] = []

    def set_attribute(self, key: str, value: object) -> None:
        self.set_attributes.append((key, value))

    def __enter__(self) -> "FakeSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None


class FakeTracer:
    """Tracer that records every started span for allowlist assertions."""

    def __init__(self) -> None:
        self.started: list[FakeSpan] = []

    def start_as_current_span(self, name: str, attributes: dict | None = None) -> FakeSpan:
        span = FakeSpan(name, attributes or {})
        self.started.append(span)
        return span


def _bind_tracing(monkeypatch, tracer: FakeTracer, module) -> None:
    """Route a module's research_span calls to the fake tracer (real sanitize kept)."""

    from deep_research_agent.observability.tracing import research_span as real_research_span

    def research_span_wrapper(name: str, attributes: dict, *, tracer=None):
        return real_research_span(name, attributes, tracer=tracer)

    monkeypatch.setattr(
        module,
        "research_span",
        lambda name, attributes: research_span_wrapper(name, attributes, tracer=tracer),
    )


# ---------------------------------------------------------------------------
# Cost tracker: contextvar attribution, price table, reset


def test_cost_tracker_attribution_follows_job_contextvar() -> None:
    tracker = CostTracker()
    token = set_job_id("job-a")
    try:
        tracker.record_llm_call(input_tokens=100, output_tokens=50, model="m1")
        tracker.record_search_call()
    finally:
        reset_job_id(token)
    tracker.record_llm_call(input_tokens=7, output_tokens=3)

    job_a = tracker.snapshot_for("job-a")
    assert job_a.llm_calls == 1
    assert job_a.total_input_tokens == 100
    assert job_a.total_output_tokens == 50
    assert job_a.search_calls == 1

    global_bucket = tracker.snapshot_for("global")
    assert global_bucket.llm_calls == 1
    assert global_bucket.total_input_tokens == 7

    assert tracker.metrics.llm_calls == 2
    assert tracker.metrics.total_tokens == 160

    tracker.reset_for("job-a")
    assert tracker.snapshot_for("job-a").llm_calls == 0
    assert tracker.metrics.llm_calls == 2


def test_cost_tracker_absent_contextvar_attributes_to_global() -> None:
    tracker = CostTracker()
    token = set_job_id("job-b")
    try:
        tracker.record_llm_call(input_tokens=10, output_tokens=10)
    finally:
        reset_job_id(token)
    assert current_job_id() == "global"
    assert tracker.snapshot_for("job-b").total_input_tokens == 10
    assert tracker.snapshot_for("global").total_tokens == 0


def test_cost_tracker_price_table_injection_and_legacy_default() -> None:
    tracker = CostTracker(
        price_table={"fast": {"in_per_million": 2.0, "out_per_million": 4.0}}
    )
    tracker.record_llm_call(input_tokens=1_000_000, output_tokens=1_000_000, model="fast")
    assert tracker.metrics.estimated_cost_usd == 6.0

    tracker.record_llm_call(input_tokens=1_000_000, output_tokens=0, model="unknown")
    assert tracker.metrics.estimated_cost_usd == 7.0

    legacy = CostTracker()
    legacy.record_llm_call(input_tokens=1000, output_tokens=1000)
    assert legacy.metrics.estimated_cost_usd == round(2000 * 0.001 / 1000, 4)


# ---------------------------------------------------------------------------
# Span wrapping: LLM calls and tool gateway invoke


class FakeUsage:
    prompt_tokens = 12
    completion_tokens = 34
    completion_tokens_details = None


class FakeMessage:
    content = "hello"
    tool_calls = []


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    usage = FakeUsage()
    choices = [FakeChoice()]


class FakeCompletions:
    async def create(self, **kwargs) -> FakeCompletion:
        return FakeCompletion()


class FakeChat:
    completions = FakeCompletions()


class FakeClient:
    chat = FakeChat()

    async def close(self) -> None:
        return None


class FakeSettings:
    llm_disable_thinking = False

    def get_llm_config(self) -> dict:
        return {
            "api_key": "test-key",
            "base_url": "http://localhost",
            "model": "test-model",
            "temperature": 0.1,
            "max_tokens": 128,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["chat", "chat_with_tools", "tool_loop"])
async def test_llm_calls_wrap_research_span_with_allowlisted_attributes(
    monkeypatch, method: str
) -> None:
    from deep_research_agent.agents import llm as llm_module
    from deep_research_agent.observability.tracing import ATTRIBUTE_NAMES

    tracker = CostTracker()
    tracer = FakeTracer()
    monkeypatch.setattr(llm_module, "get_tracker", lambda: tracker)
    _bind_tracing(monkeypatch, tracer, llm_module)

    chat = llm_module.LLMChat(settings=FakeSettings())
    chat._client = FakeClient()
    token = set_job_id("job-span")
    try:
        if method == "chat":
            content = await chat.chat("system", "user")
            assert content == "hello"
        elif method == "chat_with_tools":
            result = await chat.chat_with_tools(system="system", user="user", tools=[])
            assert result["content"] == "hello"
        else:
            result = await chat.tool_loop(
                system="system",
                user="user",
                tools=[],
                execute_tool=lambda name, arguments: {"ok": True},
            )
            assert result.content == "hello"
    finally:
        reset_job_id(token)

    assert [span.name for span in tracer.started] == ["llm.chat"]
    span = tracer.started[0]
    assert set(span.attributes) <= set(ATTRIBUTE_NAMES.values())
    assert span.attributes == {
        "research.job_id": "job-span",
        "research.model": "test-model",
        "research.retry_count": 0,
    }
    assert dict(span.set_attributes) == {
        "research.input_tokens": 12,
        "research.output_tokens": 34,
    }

    job_metrics = tracker.snapshot_for("job-span")
    assert job_metrics.llm_calls == 1
    assert job_metrics.total_input_tokens == 12
    assert job_metrics.total_output_tokens == 34
    assert job_metrics.by_model["test-model"] == {"in": 12, "out": 34}


def test_tool_gateway_invoke_wraps_research_span_with_allowlisted_attributes(monkeypatch) -> None:
    from deep_research_agent.kernel.contracts import TaskSpec
    from deep_research_agent.tool_gateway.gateway import ToolGateway
    from deep_research_agent.tool_gateway.models import (
        ToolExecutionContext,
        ToolInvocation,
    )
    from deep_research_agent.tool_gateway.registry import InMemoryToolRegistry
    from deep_research_agent.tool_gateway.registry import ToolSpec

    tracer = FakeTracer()
    from deep_research_agent.tool_gateway import gateway as gateway_module

    _bind_tracing(monkeypatch, tracer, gateway_module)

    registry = InMemoryToolRegistry()
    registry.register(
        ToolSpec(name="echo", allowed_roles=("researcher",), allowed_tenant_ids=("tenant-1",)),
        lambda arguments, context: {"echoed": arguments["text"]},
    )
    gateway = ToolGateway(registry=registry)
    task = TaskSpec(
        task_id="tool-task",
        job_id="job-tool",
        kind="research",
        role="researcher",
        objective="invoke echo",
        output_schema={
            "type": "object",
            "properties": {"echoed": {"type": "string"}},
            "additionalProperties": False,
        },
        budget={"max_tool_calls": 1},
        idempotency_key="job-tool:tool-task",
    )
    result = gateway.invoke(
        task,
        ToolInvocation(
            invocation_id="inv-1",
            tool_name="echo",
            tenant_id="tenant-1",
            idempotency_key="inv-1",
            arguments={"text": "hello"},
        ),
        ToolExecutionContext(tenant_id="tenant-1", role="researcher", job_id="job-tool"),
    )

    assert result.status == "succeeded"
    assert result.output == {"echoed": "hello"}
    assert [span.name for span in tracer.started] == ["tool.invoke"]
    span = tracer.started[0]
    assert span.attributes == {
        "research.job_id": "job-tool",
        "research.role": "researcher",
        "research.tool": "echo",
    }


# ---------------------------------------------------------------------------
# /metrics endpoint


class FakeCounter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount

    def labels(self, **kwargs) -> "FakeCounter":
        return self


class FakeGauge:
    def __init__(self, name: str) -> None:
        self.name = name
        self.values: list[float] = []

    def set(self, value: float) -> None:
        self.values.append(value)


def _install_fake_prometheus(monkeypatch, body: bytes = b"") -> types.ModuleType:
    module = types.ModuleType("prometheus_client")
    module.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    module.generate_latest = lambda registry: body
    monkeypatch.setitem(sys.modules, "prometheus_client", module)
    return module


def test_metrics_endpoint_renders_registry(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from deep_research_agent.gateway.api import create_app

    _install_fake_prometheus(monkeypatch, body=b"# exposition\nresearch_llm_calls_total 3\n")
    registry = object()
    monkeypatch.setattr(
        "deep_research_agent.observability.cost_tracker.prometheus_registry",
        lambda: registry,
    )
    monkeypatch.setattr(
        "deep_research_agent.observability.cost_tracker.refresh_prometheus_gauges",
        lambda: None,
    )

    response = TestClient(create_app(offline_mode=True)).get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "research_llm_calls_total 3" in response.text


def test_metrics_endpoint_returns_503_without_prometheus_client(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from deep_research_agent.gateway.api import create_app

    monkeypatch.setitem(sys.modules, "prometheus_client", None)

    response = TestClient(create_app(offline_mode=True)).get("/metrics")

    assert response.status_code == 503
    assert "prometheus-client" in response.json()["detail"]


def test_cost_tracker_bridge_updates_prometheus_counters_and_gauges(monkeypatch) -> None:
    import deep_research_agent.observability.cost_tracker as cost_tracker_module

    counters = {
        key: FakeCounter(key)
        for key in ("llm_calls", "search_calls", "tokens", "estimated_cost_usd")
    }
    gauges = {
        key: FakeGauge(key) for key in ("estimated_cost_usd", "task_runtime_seconds")
    }
    monkeypatch.setattr(
        cost_tracker_module,
        "_prometheus_state",
        lambda: (object(), counters, gauges),
    )

    tracker = CostTracker()
    monkeypatch.setattr(cost_tracker_module, "_tracker", tracker)
    tracker.record_llm_call(input_tokens=500, output_tokens=500, model="m1")
    tracker.record_search_call()
    cost_tracker_module.refresh_prometheus_gauges()

    assert counters["llm_calls"].value == 1
    assert counters["search_calls"].value == 1
    assert counters["tokens"].value == 1000
    assert counters["estimated_cost_usd"].value == pytest.approx(0.001)
    assert gauges["estimated_cost_usd"].values == [0.001]
    assert gauges["task_runtime_seconds"].values == [0.0]


# ---------------------------------------------------------------------------
# Offline tracing no-op and wiring


@pytest.mark.parametrize("env", [{}, {"OTEL_SDK_DISABLED": "1"}])
def test_configure_tracing_is_offline_noop_without_otel_endpoint(monkeypatch, env: dict) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from deep_research_agent.observability.tracing import configure_tracing

    tracer = configure_tracing()
    assert tracer is not None
    with tracer.start_as_current_span("offline.span") as span:
        span.set_attribute("unexported", 1)
        assert span.is_recording() is False


def test_create_app_wires_configure_tracing(monkeypatch) -> None:
    import deep_research_agent.gateway.api as api_module

    calls: list[str] = []
    monkeypatch.setattr(api_module, "configure_tracing", lambda: calls.append("configured"))
    api_module.create_app(offline_mode=True)
    assert calls == ["configured"]


def test_worker_main_wires_configure_tracing(monkeypatch) -> None:
    import deep_research_agent.research_jobs.worker as worker_module

    calls: list[str] = []

    class FakeArgs:
        scheduler_factory_path = None
        job_id = "job-1"
        workspace_dir = "/tmp/opencode/observability-worker-test"
        runtime_dirname = "research_jobs"
        heartbeat_interval_seconds = 2
        stale_timeout_seconds = 15
        offline = True

    monkeypatch.setattr(
        worker_module, "build_parser", lambda: types.SimpleNamespace(parse_args=lambda: FakeArgs())
    )
    monkeypatch.setattr(worker_module, "configure_tracing", lambda: calls.append("configured"))
    monkeypatch.setattr(worker_module, "get_settings", lambda: None)

    service = types.SimpleNamespace(
        get=lambda job_id: None,
        configure_scheduler_factory=lambda factory: None,
        store=types.SimpleNamespace(
            acquire_worker_lease=lambda *args, **kwargs: None,
            heartbeat=lambda *args, **kwargs: None,
            clear_worker=lambda *args, **kwargs: None,
        ),
        run_job=lambda job_id, worker_lease_id=None: None,
    )
    monkeypatch.setattr(worker_module, "ResearchJobService", lambda **kwargs: service)

    worker_module.main()

    assert calls == ["configured"]


# ---------------------------------------------------------------------------
# Cost metrics land in the scheduler bundle


@pytest.mark.asyncio
async def test_scheduler_bundle_carries_cost_metrics_in_run_manifest(tmp_path: Path) -> None:
    from deep_research_agent.kernel.contracts import TaskResult, TaskSpec
    from deep_research_agent.orchestration.dag import ResearchDAG
    from deep_research_agent.orchestration.scheduler import ResearchScheduler
    from deep_research_agent.orchestration.workers import WorkerOutput
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator
    from deep_research_agent.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="cost bundle",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )

    token = set_job_id(job.job_id)
    try:
        get_tracker().record_llm_call(input_tokens=120, output_tokens=40, model="test-model")
    finally:
        reset_job_id(token)

    class CompletedWorker:
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            assert current_job_id() == task.job_id
            return WorkerOutput(
                result=TaskResult(task_id=task.task_id, job_id=task.job_id, status="completed"),
                output={"task_id": task.task_id},
            )

    task = TaskSpec(
        task_id="cost-task",
        job_id=job.job_id,
        kind="research",
        role="researcher",
        objective="measure cost",
        output_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
            "additionalProperties": False,
        },
        budget={"max_tool_calls": 1},
        idempotency_key=f"{job.job_id}:cost-task",
    )
    scheduler = ResearchScheduler(worker=CompletedWorker(), max_workers=1)
    result = await ResearchJobOrchestrator(service=service, scheduler=scheduler).run_dag(
        job.job_id,
        ResearchDAG(job_id=job.job_id, tasks=[task]),
        {"version_id": "config-v1"},
    )

    assert result.status == "completed"
    completed = service.get(job.job_id)
    bundle = json.loads(Path(completed.report_bundle_path).read_text(encoding="utf-8"))
    cost_metrics = bundle["run_manifest"]["cost_metrics"]
    assert cost_metrics["llm_calls"] == 1
    assert cost_metrics["total_input_tokens"] == 120
    assert cost_metrics["total_output_tokens"] == 40
    assert cost_metrics["estimated_cost_usd"] == 0.0002
    assert current_job_id() == "global"
