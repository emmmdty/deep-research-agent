"""Deterministic acceptance tests for the V2 multi-agent runtime."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    EvidencePacket,
    EvidenceSpan,
    ResearchBrief,
    TaskResult,
    TaskSpec,
)
from deep_research_agent.model_runtime.models import (
    AgentRoleProfile,
    JobRuntimeSnapshot,
    ModelEndpoint,
    RuntimeConfigVersion,
)
from deep_research_agent.orchestration.dag import ResearchDAG, ResearchPlanner
from deep_research_agent.orchestration.events import CancellationToken, InMemoryRunJournal
from deep_research_agent.orchestration.reducer import EvidenceReducer
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
from deep_research_agent.orchestration.workers import WorkerOutput
from deep_research_agent.tool_gateway.gateway import ToolGateway
from deep_research_agent.tool_gateway.models import ToolInvocation, ToolSpec
from deep_research_agent.tool_gateway.registry import InMemoryToolRegistry


def _task(
    task_id: str,
    *,
    depends_on: tuple[str, ...] = (),
    schema: dict[str, Any] | None = None,
    role: str = "researcher",
) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        job_id="job-1",
        kind="research",
        role=role,
        objective=f"execute {task_id}",
        depends_on=list(depends_on),
        input_artifacts=[],
        output_schema=schema
        or {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
            "additionalProperties": False,
        },
        budget={"max_tool_calls": 1},
        idempotency_key=f"job-1:{task_id}",
    )


def _completed(task: TaskSpec, output: dict[str, Any], *, spawned: list[TaskSpec] | None = None) -> WorkerOutput:
    return WorkerOutput(
        result=TaskResult(task_id=task.task_id, job_id=task.job_id, status="completed"),
        output=output,
        spawned_tasks=spawned or [],
    )


def _config_snapshot(job_id: str = "job-1") -> JobRuntimeSnapshot:
    version = RuntimeConfigVersion(
        version_id="config-v1",
        endpoints=(
            ModelEndpoint(
                endpoint_id="research-primary",
                base_url="https://model.example/v1",
                model="research-model",
                credential_id="research-key",
                tier="standard",
            ),
        ),
        role_profiles=(
            AgentRoleProfile(
                role="researcher",
                tier="standard",
                endpoint_ids=("research-primary",),
            ),
        ),
    )
    return JobRuntimeSnapshot(
        job_id=job_id,
        version=version,
        fallback_chains={"researcher": ("research-primary",)},
    )


class DeterministicWorker:
    """Cooperative worker that exposes scheduling behavior without external I/O."""

    def __init__(self, *, delay: float = 0.01) -> None:
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self.calls: Counter[str] = Counter()
        self.started: list[str] = []
        self.finished: list[str] = []

    async def execute(self, task: TaskSpec, context) -> WorkerOutput:
        self.calls[task.task_id] += 1
        self.started.append(task.task_id)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
            self.finished.append(task.task_id)
            return _completed(task, {"task_id": task.task_id})
        finally:
            self.active -= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 4, 8])
async def test_scheduler_honors_one_four_and_eight_worker_concurrency(limit: int) -> None:
    worker = DeterministicWorker()
    dag = ResearchDAG(job_id="job-1", tasks=[_task(f"task-{index}") for index in range(8)])

    result = await ResearchScheduler(worker=worker, max_workers=limit).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
        dag,
        {"version_id": "config-v1"},
    )

    assert result.status == "completed"
    assert worker.max_active == limit
    assert set(result.task_results) == {f"task-{index}" for index in range(8)}


def test_scheduler_rejects_more_than_eight_active_workers() -> None:
    with pytest.raises(ValueError, match="at most 8"):
        ResearchScheduler(worker=DeterministicWorker(), max_workers=9)


@pytest.mark.asyncio
async def test_scheduler_starts_tasks_only_after_dependencies_complete() -> None:
    class DependencyWorker(DeterministicWorker):
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            if task.task_id == "merge":
                assert set(context.dependency_results) == {"left", "right"}
                assert set(self.finished) == {"left", "right"}
            return await super().execute(task, context)

    worker = DependencyWorker(delay=0)
    dag = ResearchDAG(
        job_id="job-1",
        tasks=[_task("merge", depends_on=("left", "right")), _task("right"), _task("left")],
    )

    result = await ResearchScheduler(worker=worker, max_workers=4).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"), dag, {"version_id": "config-v1"}
    )

    assert result.status == "completed"
    assert worker.started[-1] == "merge"


@pytest.mark.asyncio
async def test_scheduler_accepts_dynamic_fan_out_without_rerunning_parent() -> None:
    class FanOutWorker(DeterministicWorker):
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            self.calls[task.task_id] += 1
            if task.task_id == "seed":
                children = [_task("child-b", depends_on=("seed",)), _task("child-a", depends_on=("seed",))]
                return _completed(task, {"task_id": task.task_id}, spawned=children)
            return _completed(task, {"task_id": task.task_id})

    worker = FanOutWorker(delay=0)
    result = await ResearchScheduler(worker=worker, max_workers=4).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
        ResearchDAG(job_id="job-1", tasks=[_task("seed")]),
        {"version_id": "config-v1"},
    )

    assert result.status == "completed"
    assert set(result.task_results) == {"seed", "child-a", "child-b"}
    assert worker.calls == Counter({"seed": 1, "child-a": 1, "child-b": 1})


@pytest.mark.asyncio
async def test_scheduler_cancellation_stops_running_and_pending_tasks() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    token = CancellationToken()

    class BlockingWorker:
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            entered.set()
            await release.wait()
            return _completed(task, {"task_id": task.task_id})

    scheduler = ResearchScheduler(worker=BlockingWorker(), max_workers=2, cancellation_token=token)
    run = asyncio.create_task(
        scheduler.run(
            SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
            ResearchDAG(job_id="job-1", tasks=[_task(f"task-{index}") for index in range(4)]),
            {"version_id": "config-v1"},
        )
    )
    await entered.wait()
    token.cancel()

    result = await asyncio.wait_for(run, timeout=1)

    assert result.status == "cancelled"
    assert {item.status for item in result.task_results.values()} == {"cancelled"}
    assert result.events[-1].event_type == "run.cancelled"


@pytest.mark.asyncio
async def test_scheduler_polls_external_cancellation_while_workers_are_running() -> None:
    entered = asyncio.Event()
    cancel_requested = False

    class SlowWorker:
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            entered.set()
            await asyncio.sleep(0.2)
            return _completed(task, {"task_id": task.task_id})

    scheduler = ResearchScheduler(
        worker=SlowWorker(),
        max_workers=1,
        cancellation_check=lambda: cancel_requested,
        cancellation_poll_seconds=0.01,
    )
    run = asyncio.create_task(
        scheduler.run(
            SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
            ResearchDAG(job_id="job-1", tasks=[_task("slow")]),
            {"version_id": "config-v1"},
        )
    )
    await entered.wait()
    cancel_requested = True

    result = await asyncio.wait_for(run, timeout=0.5)

    assert result.status == "cancelled"
    assert result.task_results["slow"].status == "cancelled"


@pytest.mark.asyncio
async def test_scheduler_retries_only_the_failed_branch() -> None:
    class FlakyBranchWorker(DeterministicWorker):
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            self.calls[task.task_id] += 1
            if task.task_id == "left" and self.calls[task.task_id] == 1:
                raise RuntimeError("transient left failure")
            return _completed(task, {"task_id": task.task_id})

    worker = FlakyBranchWorker(delay=0)
    dag = ResearchDAG(
        job_id="job-1",
        tasks=[
            _task("left"),
            _task("left-child", depends_on=("left",)),
            _task("right"),
            _task("right-child", depends_on=("right",)),
        ],
    )

    result = await ResearchScheduler(worker=worker, max_workers=4, max_attempts=2).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"), dag, {"version_id": "config-v1"}
    )

    assert result.status == "completed"
    assert worker.calls == Counter({"left": 2, "left-child": 1, "right": 1, "right-child": 1})
    assert [event.task_id for event in result.events if event.event_type == "task.retry_scheduled"] == ["left"]


@pytest.mark.asyncio
async def test_scheduler_events_and_checkpoints_have_monotonic_sequences() -> None:
    journal = InMemoryRunJournal()
    result = await ResearchScheduler(
        worker=DeterministicWorker(delay=0), max_workers=2, journal=journal
    ).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
        ResearchDAG(job_id="job-1", tasks=[_task("one"), _task("two")]),
        {"version_id": "config-v1"},
    )

    assert [event.sequence for event in result.events] == list(range(1, len(result.events) + 1))
    assert [checkpoint.sequence for checkpoint in result.checkpoints] == [1, 2]
    assert journal.events == result.events
    assert journal.checkpoints == result.checkpoints


@pytest.mark.asyncio
async def test_scheduler_rejects_worker_output_that_violates_declared_schema() -> None:
    class InvalidWorker:
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            return _completed(task, {"count": "not-an-integer"})

    task = _task(
        "invalid",
        schema={
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
            "additionalProperties": False,
        },
    )
    result = await ResearchScheduler(worker=InvalidWorker(), max_workers=1, max_attempts=1).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
        ResearchDAG(job_id="job-1", tasks=[task]),
        {"version_id": "config-v1"},
    )

    assert result.status == "failed"
    assert result.task_results["invalid"].status == "failed"
    assert "output schema" in (result.task_results["invalid"].error or "")


@pytest.mark.asyncio
async def test_failed_task_retry_does_not_duplicate_idempotent_tool_side_effect() -> None:
    side_effects: list[str] = []
    registry = InMemoryToolRegistry()
    registry.register(
        ToolSpec(
            name="snapshot",
            allowed_roles=("researcher",),
            allowed_tenant_ids=("tenant-1",),
            retry_safety="adapter_idempotent",
        ),
        lambda arguments, context: side_effects.append(context.idempotency_key) or {"saved": arguments["url"]},
    )
    gateway = ToolGateway(registry=registry)

    class ToolThenFailWorker:
        attempts = 0

        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            self.attempts += 1
            envelope = await context.invoke_tool(
                ToolInvocation(
                    invocation_id=f"snapshot-attempt-{self.attempts}",
                    tool_name="snapshot",
                    tenant_id="tenant-1",
                    idempotency_key=f"worker-attempt-{self.attempts}",
                    arguments={"url": "https://example.com/source-1"},
                )
            )
            assert envelope.status == "succeeded"
            if self.attempts == 1:
                raise RuntimeError("checkpoint lost after tool success")
            assert envelope.duplicate is True
            return _completed(task, {"task_id": task.task_id})

    worker = ToolThenFailWorker()
    result = await ResearchScheduler(
        worker=worker, max_workers=1, max_attempts=2, tool_gateway=gateway
    ).run(
        SchedulerJob(job_id="job-1", tenant_id="tenant-1"),
        ResearchDAG(job_id="job-1", tasks=[_task("snapshot-task")]),
        {"version_id": "config-v1"},
    )

    assert result.status == "completed"
    assert worker.attempts == 2
    assert len(side_effects) == 1
    assert side_effects[0].startswith("job-1:snapshot-task:snapshot:")


def test_research_planner_builds_domain_neutral_dag() -> None:
    from deep_research_agent.domain_packs.models import DomainPack

    brief = ResearchBrief(
        brief_id="brief-1",
        job_id="job-1",
        question="How should this dependency be assessed?",
        domain_pack_id="software-supply-chain-smoke",
        objectives=["Assess provenance", "Assess maintenance"],
    )
    pack = DomainPack(
        schema_version="1.0",
        pack_id="software-supply-chain-smoke",
        version="1",
        title="Supply chain",
        description="Generic dependency research",
        entity_types=["package"],
        relations=[],
        research_questions=["What is the provenance?"],
        source_types=["registry"],
    )

    dag = ResearchPlanner().plan(brief, pack)

    assert dag.job_id == brief.job_id
    assert dag.tasks[-1].role == "critic"
    assert set(dag.tasks[-1].depends_on) == {task.task_id for task in dag.tasks[:-1]}


def test_dag_rejects_unknown_dependencies_and_cycles() -> None:
    with pytest.raises(ValueError, match="unknown dependencies"):
        ResearchDAG(job_id="job-1", tasks=[_task("orphan", depends_on=("missing",))])
    with pytest.raises(ValueError, match="cycle"):
        ResearchDAG(
            job_id="job-1",
            tasks=[_task("left", depends_on=("right",)), _task("right", depends_on=("left",))],
        )
    with pytest.raises(ValueError, match="idempotency keys"):
        ResearchDAG(
            job_id="job-1",
            tasks=[
                _task("left"),
                _task("right").model_copy(update={"idempotency_key": "job-1:left"}),
            ],
        )


def test_reducer_deduplicates_exact_records_without_resolving_disagreement() -> None:
    span = EvidenceSpan(
        span_id="span-1",
        document_version_id="doc-v1",
        page=3,
        quote="The measured value was 42.",
        extraction_method="pdf_text",
    )
    accepted = ClaimRecord(
        claim_id="claim-a",
        claim="The measured value was 42.",
        claim_type="measurement",
        support_status="accepted",
        confidence=0.9,
        evidence_spans=[span],
    )
    contradicted = accepted.model_copy(
        update={"claim_id": "claim-b", "support_status": "contradicted", "confidence": 0.8}
    )
    packet_a = EvidencePacket(packet_id="packet-a", task_id="left", evidence_spans=[span], claims=[accepted])
    packet_b = EvidencePacket(
        packet_id="packet-b", task_id="right", evidence_spans=[span], claims=[accepted, contradicted]
    )

    reduced = EvidenceReducer().reduce([packet_b, packet_a, packet_a])

    assert [item.span_id for item in reduced.evidence_spans] == ["span-1"]
    assert [item.claim_id for item in reduced.claims] == ["claim-a", "claim-b"]
    assert reduced.semantic_disagreements == [("claim-a", "claim-b")]


def test_reducer_merges_semantic_duplicate_claims_and_documents_deterministically() -> None:
    span_a = EvidenceSpan(
        span_id="span-a",
        document_version_id="doc-v1",
        page=1,
        quote="The result is reproducible.",
        extraction_method="pdf_text",
    )
    span_b = span_a.model_copy(update={"span_id": "span-b", "page": 2})
    claim_b = ClaimRecord(
        claim_id="claim-b",
        claim="  The result is reproducible. ",
        claim_type="result",
        support_status="accepted",
        confidence=0.8,
        evidence_spans=[span_b],
    )
    claim_a = claim_b.model_copy(
        update={"claim_id": "claim-a", "claim": "The result is reproducible.", "evidence_spans": [span_a]}
    )
    artifact_b = ArtifactRef(
        artifact_id="source-b",
        uri="artifact://source-b",
        media_type="application/pdf",
        content_sha256="a" * 64,
    )
    artifact_a = artifact_b.model_copy(update={"artifact_id": "source-a", "uri": "artifact://source-a"})

    reduced = EvidenceReducer().reduce(
        [
            EvidencePacket(
                packet_id="packet-b",
                task_id="right",
                claims=[claim_b],
                artifacts=[artifact_b],
            ),
            EvidencePacket(
                packet_id="packet-a",
                task_id="left",
                claims=[claim_a],
                artifacts=[artifact_a],
            ),
        ]
    )

    assert [claim.claim_id for claim in reduced.claims] == ["claim-a"]
    assert [span.span_id for span in reduced.claims[0].evidence_spans] == ["span-a", "span-b"]
    assert [artifact.artifact_id for artifact in reduced.artifacts] == ["source-a"]


def test_orchestration_modules_do_not_import_provider_sdks() -> None:
    orchestration_dir = Path(__file__).parents[1] / "src" / "deep_research_agent" / "orchestration"
    source = "\n".join(path.read_text(encoding="utf-8") for path in orchestration_dir.glob("*.py"))

    assert "import openai" not in source
    assert "from openai" not in source
    assert "pydantic_ai" not in source


@pytest.mark.asyncio
async def test_job_orchestrator_bridges_new_runs_to_scheduler_and_persists_checkpoints(tmp_path) -> None:
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator
    from deep_research_agent.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="scheduler bridge",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )
    dag = ResearchDAG(
        job_id=job.job_id,
        tasks=[_task("bridge-task").model_copy(update={"job_id": job.job_id})],
    )
    scheduler = ResearchScheduler(worker=DeterministicWorker(delay=0), max_workers=1)

    snapshot = _config_snapshot(job.job_id)
    result = await ResearchJobOrchestrator(service=service, scheduler=scheduler).run_dag(
        job.job_id,
        dag,
        snapshot,
    )

    loaded = service.get(job.job_id)
    assert loaded is not None
    assert result.status == "completed"
    assert loaded.status == "completed"
    assert loaded.runtime_path == "scheduler-v2"
    assert loaded.metadata["scheduler_config_snapshot"]["version"]["version_id"] == "config-v1"
    checkpoint_path = Path(loaded.metadata["scheduler_checkpoint_path"])
    assert checkpoint_path.exists()
    assert json.loads(checkpoint_path.read_text(encoding="utf-8"))[0]["task_id"] == "bridge-task"
    scheduler_events = [event for event in service.list_events(job.job_id) if event.stage == "scheduler"]
    assert [event.payload["scheduler_sequence"] for event in scheduler_events] == list(
        range(1, len(scheduler_events) + 1)
    )


@pytest.mark.asyncio
async def test_job_orchestrator_fences_scheduler_writes_after_losing_lease(tmp_path) -> None:
    from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator
    from deep_research_agent.research_jobs.service import ResearchJobService
    from deep_research_agent.research_jobs.store import WorkerLeaseConflict

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="scheduler lease fence",
        max_loops=1,
        research_profile="default",
        start_worker=False,
    )
    service.store.acquire_worker_lease(job.job_id, worker_pid=111, lease_id="lease-a")

    class LeaseStealingWorker:
        async def execute(self, task: TaskSpec, context) -> WorkerOutput:
            service.store.clear_worker(job.job_id, lease_id="lease-a")
            service.store.acquire_worker_lease(job.job_id, worker_pid=222, lease_id="lease-b")
            return _completed(task, {"task_id": task.task_id})

    scheduler = ResearchScheduler(worker=LeaseStealingWorker(), max_workers=1)
    dag = ResearchDAG(
        job_id=job.job_id,
        tasks=[_task("bridge-task").model_copy(update={"job_id": job.job_id})],
    )

    with pytest.raises(WorkerLeaseConflict):
        await ResearchJobOrchestrator(
            service=service,
            scheduler=scheduler,
            worker_lease_id="lease-a",
        ).run_dag(job.job_id, dag, _config_snapshot(job.job_id))

    assert not (service.store.job_dir(job.job_id) / "scheduler_checkpoints.json").exists()
    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.worker_lease_id == "lease-b"
