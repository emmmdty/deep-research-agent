"""Phase 02 job orchestrator、runtime contracts 与存储回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from legacy.workflows.states import CriticFeedback, EvidenceNote, ReportArtifact, RunMetrics, SourceRecord, TaskItem


PHASE2_SCHEMA_NAMES = [
    "job-runtime-record",
    "job-progress-event",
    "job-checkpoint",
]


def _build_runtime_record() -> dict:
    return {
        "job_id": "job-phase2-001",
        "topic": "可信深度研究 app",
        "status": "running",
        "current_stage": "collecting",
        "created_at": "2026-04-09T00:00:00+00:00",
        "updated_at": "2026-04-09T00:00:10+00:00",
        "attempt_index": 1,
        "retry_of": None,
        "cancel_requested": False,
        "worker_pid": 12345,
        "worker_lease_id": "lease-001",
        "last_heartbeat_at": "2026-04-09T00:00:10+00:00",
        "active_checkpoint_id": "checkpoint-001",
        "report_path": "workspace/research_jobs/job-phase2-001/report.md",
        "report_bundle_path": "workspace/research_jobs/job-phase2-001/bundle/report_bundle.json",
        "trace_path": "workspace/research_jobs/job-phase2-001/bundle/trace.jsonl",
        "runtime_path": "orchestrator-v1",
        "source_profile": "company_trusted",
        "budget": {
            "max_candidates_per_connector": 4,
            "max_fetches_per_task": 3,
            "max_total_fetches": 8,
        },
        "policy_overrides": {"allow_domains": ["docs.langchain.com"]},
        "connector_health": {
            "open_web": {
                "connector_name": "open_web",
                "search_attempts": 1,
                "search_successes": 1,
                "fetch_attempts": 1,
                "fetch_successes": 1,
                "policy_blocked": 0,
                "error_count": 0,
                "last_error": None,
            }
        },
        "audit_gate_status": "unchecked",
        "critical_claim_count": 0,
        "blocked_critical_claim_count": 0,
        "audit_graph_path": "workspace/research_jobs/job-phase2-001/audit/claim_graph.json",
        "review_queue_path": "workspace/research_jobs/job-phase2-001/audit/review_queue.json",
        "error": None,
        "metadata": {"research_profile": "default", "source_profile": "default"},
    }


def _build_progress_event() -> dict:
    return {
        "event_id": "event-001",
        "job_id": "job-phase2-001",
        "sequence": 1,
        "stage": "collecting",
        "event_type": "stage.started",
        "timestamp": "2026-04-09T00:00:10+00:00",
        "message": "开始 collecting 阶段",
        "payload": {"pending_tasks": 1},
    }


def _build_checkpoint() -> dict:
    return {
        "checkpoint_id": "checkpoint-001",
        "job_id": "job-phase2-001",
        "stage": "planned",
        "sequence": 1,
        "loop_count": 0,
        "created_at": "2026-04-09T00:00:10+00:00",
        "next_stage": "collecting",
        "state_payload": {
            "research_topic": "可信深度研究 app",
            "research_profile": "default",
            "tasks": [
                {
                    "id": 1,
                    "title": "梳理目标",
                    "intent": "确认当前目标",
                    "query": "可信深度研究 app",
                    "status": "pending",
                }
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "evidence_notes": [],
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "available_capabilities": [],
            "capability_plan": {},
            "tool_invocations": [],
            "coverage_status": {},
            "loop_count": 0,
            "max_loops": 2,
            "quality_gate_status": "unchecked",
            "quality_gate_fail_reason": "",
            "status": "planned",
            "error": None,
            "pending_follow_up_queries": [],
        },
    }


@pytest.mark.parametrize("schema_name", PHASE2_SCHEMA_NAMES)
def test_phase2_runtime_schemas_are_loadable(schema_name: str):
    """Phase 02 runtime schema 应存在且可加载。"""
    from artifacts.schemas import load_schema

    schema = load_schema(schema_name)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"


def test_phase2_runtime_schema_validation():
    """Phase 02 runtime fixtures 应通过 schema 校验。"""
    from artifacts.schemas import validate_instance

    validate_instance("job-runtime-record", _build_runtime_record())
    validate_instance("job-progress-event", _build_progress_event())
    validate_instance("job-checkpoint", _build_checkpoint())


def test_job_runtime_record_rejects_legacy_needs_review_status():
    """needs_review 不应再作为生命周期终态存在。"""
    from pydantic import ValidationError

    from services.research_jobs.models import JobRuntimeRecord

    payload = _build_runtime_record()
    payload["status"] = "needs_review"

    with pytest.raises(ValidationError):
        JobRuntimeRecord.model_validate(payload)


def test_phase2_checkpoint_schema_rejects_missing_state_payload():
    """job checkpoint 缺少 state_payload 时应校验失败。"""
    from artifacts.schemas import validate_instance

    payload = _build_checkpoint()
    payload.pop("state_payload")

    with pytest.raises(ValidationError):
        validate_instance("job-checkpoint", payload)


def test_job_store_persists_jobs_events_and_checkpoints(tmp_path: Path):
    """job store 应持久化 runtime record、event 与 checkpoint。"""
    from services.research_jobs.models import JobCheckpoint, JobProgressEvent, JobRuntimeRecord
    from services.research_jobs.store import ResearchJobStore

    store = ResearchJobStore(workspace_dir=str(tmp_path))
    job = JobRuntimeRecord.model_validate(_build_runtime_record())
    event = JobProgressEvent.model_validate(_build_progress_event())
    checkpoint = JobCheckpoint.model_validate(_build_checkpoint())

    store.upsert_job(job)
    store.append_event(event)
    store.save_checkpoint(checkpoint)

    loaded_job = store.get_job(job.job_id)
    loaded_events = store.list_events(job.job_id)
    latest_checkpoint = store.get_latest_checkpoint(job.job_id)

    assert loaded_job is not None
    assert loaded_job.runtime_path == "orchestrator-v1"
    assert loaded_job.source_profile == "company_trusted"
    assert len(loaded_events) == 1
    assert loaded_events[0].event_type == "stage.started"
    assert latest_checkpoint is not None
    assert latest_checkpoint.next_stage == "collecting"


def test_job_store_rejects_second_active_worker_lease(tmp_path: Path):
    """已有活跃 lease 时，第二个 worker 不应覆盖当前 lease。"""
    from services.research_jobs.models import JobRuntimeRecord
    from services.research_jobs.store import ResearchJobStore, WorkerLeaseConflict

    store = ResearchJobStore(workspace_dir=str(tmp_path))
    payload = _build_runtime_record()
    payload["worker_pid"] = None
    payload["worker_lease_id"] = None
    payload["last_heartbeat_at"] = None
    store.upsert_job(JobRuntimeRecord.model_validate(payload))

    first = store.acquire_worker_lease(payload["job_id"], worker_pid=111, lease_id="lease-a")

    assert first.worker_lease_id == "lease-a"
    with pytest.raises(WorkerLeaseConflict):
        store.acquire_worker_lease(payload["job_id"], worker_pid=222, lease_id="lease-b")

    loaded = store.get_job(payload["job_id"])
    assert loaded is not None
    assert loaded.worker_pid == 111
    assert loaded.worker_lease_id == "lease-a"


def test_job_store_only_matching_lease_can_clear_worker(tmp_path: Path):
    """旧 worker 退出时不能清理新 worker 的 lease。"""
    from services.research_jobs.models import JobRuntimeRecord
    from services.research_jobs.store import ResearchJobStore

    store = ResearchJobStore(workspace_dir=str(tmp_path))
    payload = _build_runtime_record()
    payload["worker_pid"] = None
    payload["worker_lease_id"] = None
    payload["last_heartbeat_at"] = None
    store.upsert_job(JobRuntimeRecord.model_validate(payload))
    store.acquire_worker_lease(payload["job_id"], worker_pid=111, lease_id="lease-a")

    mismatch = store.clear_worker(payload["job_id"], lease_id="lease-b")

    assert mismatch.worker_lease_id == "lease-a"
    cleared = store.clear_worker(payload["job_id"], lease_id="lease-a")
    assert cleared.worker_pid is None
    assert cleared.worker_lease_id is None


def test_orchestrator_rejects_mismatched_worker_lease(tmp_path: Path):
    """lease 不匹配的 worker 不应推进 job 阶段。"""
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService
    from services.research_jobs.store import WorkerLeaseConflict

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="lease fencing", max_loops=1, research_profile="default", start_worker=False)
    service.store.acquire_worker_lease(job.job_id, worker_pid=111, lease_id="lease-a")
    orchestrator = ResearchJobOrchestrator(service=service, worker_lease_id="lease-b")

    with pytest.raises(WorkerLeaseConflict):
        orchestrator.run(job.job_id)

    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.status == "created"
    assert loaded.current_stage == "clarifying"


def test_orchestrator_fences_writes_after_worker_loses_lease(tmp_path: Path):
    """worker 阶段执行中丢失 lease 后，不能继续写 checkpoint / completed event。"""
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService
    from services.research_jobs.store import WorkerLeaseConflict

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="lease lost during stage", max_loops=1, research_profile="default", start_worker=False)
    service.store.update_job_status(job.job_id, status="running", current_stage="planned")
    service.store.acquire_worker_lease(job.job_id, worker_pid=111, lease_id="lease-a")

    def steal_lease(state):
        service.store.clear_worker(job.job_id, lease_id="lease-a")
        service.store.acquire_worker_lease(job.job_id, worker_pid=222, lease_id="lease-b")
        return {
            "tasks": [TaskItem(id=1, title="lease", intent="验证 lease fence", query="lease")],
            "status": "planned",
        }

    orchestrator = ResearchJobOrchestrator(
        service=service,
        worker_lease_id="lease-a",
        planner_fn=steal_lease,
    )

    with pytest.raises(WorkerLeaseConflict):
        orchestrator.run(job.job_id)

    events = service.list_events(job.job_id)
    assert not any(event.stage == "planned" and event.event_type == "stage.completed" for event in events)
    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.worker_lease_id == "lease-b"


def test_job_events_are_append_only_when_caller_reuses_sequence(tmp_path: Path):
    """event 写入应由 store 分配单调序号，不能覆盖同一 sequence。"""
    from services.research_jobs.models import JobProgressEvent, JobRuntimeRecord
    from services.research_jobs.store import ResearchJobStore

    store = ResearchJobStore(workspace_dir=str(tmp_path))
    job = JobRuntimeRecord.model_validate(_build_runtime_record())
    store.upsert_job(job)
    event = JobProgressEvent.model_validate(_build_progress_event())
    duplicate_sequence = event.model_copy(update={"event_type": "stage.completed"})

    first = store.append_event(event)
    second = store.append_event(duplicate_sequence)
    events = store.list_events(job.job_id)

    assert [item.sequence for item in events] == [1, 2]
    assert first.event_id.endswith("0001")
    assert second.event_id.endswith("0002")
    assert [item.event_type for item in events] == ["stage.started", "stage.completed"]


def test_job_checkpoints_are_append_only_when_caller_reuses_sequence(tmp_path: Path):
    """checkpoint 写入应由 store 分配单调序号，不能覆盖同一 sequence。"""
    from services.research_jobs.models import JobCheckpoint, JobRuntimeRecord, RuntimeStage
    from services.research_jobs.store import ResearchJobStore

    store = ResearchJobStore(workspace_dir=str(tmp_path))
    job = JobRuntimeRecord.model_validate(_build_runtime_record())
    store.upsert_job(job)
    checkpoint = JobCheckpoint.model_validate(_build_checkpoint())
    duplicate_sequence = checkpoint.model_copy(update={"next_stage": RuntimeStage.EXTRACTING})

    first = store.save_checkpoint(checkpoint)
    second = store.save_checkpoint(duplicate_sequence)
    latest = store.get_latest_checkpoint(job.job_id)

    assert first.sequence == 1
    assert second.sequence == 2
    assert latest is not None
    assert latest.sequence == 2
    assert latest.next_stage == "extracting"
    assert (store.checkpoint_dir(job.job_id) / "0001-planned.json").exists()
    assert (store.checkpoint_dir(job.job_id) / "0002-planned.json").exists()


def test_orchestrator_runs_happy_path_and_emits_bundle(tmp_path: Path):
    """orchestrator 应能跑完整 happy path，并输出 report/bundle/trace。"""
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 happy path", max_loops=2, research_profile="default", start_worker=False)

    source = SourceRecord(
        citation_id=1,
        source_type="web",
        query="phase2 happy path",
        title="可信深度研究 app",
        url="https://example.com/phase2",
        snippet="phase2 需要可恢复的 job orchestrator。",
        selected=True,
        trust_tier=4,
    )

    orchestrator = ResearchJobOrchestrator(
        service=service,
        planner_fn=lambda state: {
            "tasks": [TaskItem(id=1, title="拆解任务", intent="规划", query="phase2 happy path")],
            "status": "planned",
        },
        collect_step_fn=lambda state: (
            {
                "tasks": [
                    TaskItem(
                        id=1,
                        title="拆解任务",
                        intent="规划",
                        query="phase2 happy path",
                        status="completed",
                        summary="phase2 需要 job orchestrator。[1]",
                        sources="[1]",
                    )
                ],
                "task_summaries": ["phase2 需要 job orchestrator。[1]"],
                "sources_gathered": [source],
                "evidence_notes": [],
                "status": "researched",
            },
            False,
        ),
        verifier_fn=lambda state: {
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": state.get("memory_stats"),
            "run_metrics": state.get("run_metrics"),
            "status": "verified",
        },
        critic_fn=lambda state: {
            "critic_feedback": CriticFeedback(
                quality_score=8,
                is_sufficient=True,
                gaps=[],
                follow_up_queries=[],
                feedback="已足够",
            ),
            "loop_count": 1,
            "run_metrics": RunMetrics(status="reviewed"),
            "status": "reviewed",
        },
        writer_fn=lambda state: {
            "final_report": "# 报告\n\nphase2 需要 job orchestrator。[1]",
            "report_artifact": ReportArtifact(
                topic=state["research_topic"],
                report="# 报告\n\nphase2 需要 job orchestrator。[1]",
                citations=[source],
                metrics=RunMetrics(status="completed"),
            ),
            "status": "completed",
        },
    )

    final_job = orchestrator.run(job.job_id)

    assert final_job.status == "completed"
    assert Path(final_job.report_path).exists()
    assert Path(final_job.report_bundle_path).exists()
    assert Path(final_job.trace_path).exists()

    bundle = json.loads(Path(final_job.report_bundle_path).read_text(encoding="utf-8"))
    from artifacts.schemas import validate_instance

    validate_instance("report-bundle", bundle)
    assert bundle["job"]["runtime_path"] == "orchestrator-v1"


def test_job_service_cancel_and_retry_flow(tmp_path: Path):
    """service 应支持 cancel 请求与基于失败 job 的 retry。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 retry", max_loops=2, research_profile="default", start_worker=False)

    cancelled = service.cancel(job.job_id)
    service.store.update_job_status(job.job_id, status="failed", error="测试失败")
    retried = service.retry(job.job_id, start_worker=False)

    assert cancelled.cancel_requested is True
    assert retried.retry_of == job.job_id
    assert retried.attempt_index == 2


def test_job_service_resume_reuses_latest_checkpoint(tmp_path: Path):
    """resume 应复用同一 job，并从最新 checkpoint 的 next_stage 恢复。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 resume", max_loops=2, research_profile="default", start_worker=False)
    service.store.update_job_status(job.job_id, status="failed", current_stage="failed", error="phase2 failed")

    resumed = service.resume(job.job_id, start_worker=False)

    assert resumed.job_id == job.job_id
    assert resumed.status == "created"
    assert resumed.current_stage == "clarifying"
    assert resumed.error is None
    assert any(event.event_type == "job.resumed" for event in service.list_events(job.job_id))


def test_job_service_refine_restarts_from_safe_boundary(tmp_path: Path):
    """refine 应记录 refinement event，并从安全边界恢复。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 refine", max_loops=2, research_profile="default", start_worker=False)
    service.store.update_job_status(job.job_id, status="failed", current_stage="failed", error="phase2 failed")

    refined = service.refine(
        job.job_id,
        "Expand competitor coverage for Anthropic and OpenAI.",
        start_worker=False,
    )
    checkpoint = service.store.get_checkpoint(refined.job_id, refined.active_checkpoint_id or "")

    assert refined.job_id == job.job_id
    assert refined.status == "created"
    assert refined.current_stage == "planned"
    assert checkpoint is not None
    assert checkpoint.next_stage == "planned"
    assert checkpoint.state_payload["refinement_history"][-1]["instruction"].startswith("Expand competitor")
    assert any(event.event_type == "job.refine_requested" for event in service.list_events(job.job_id))


def test_job_service_cancel_is_idempotent(tmp_path: Path):
    """重复 cancel 不应重复追加 cancel_requested event。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 cancel idempotency", max_loops=2, research_profile="default", start_worker=False)

    first = service.cancel(job.job_id)
    second = service.cancel(job.job_id)
    events = service.list_events(job.job_id)

    assert first.cancel_requested is True
    assert second.cancel_requested is True
    assert [event.event_type for event in events].count("job.cancel_requested") == 1


def test_job_service_cancel_terminal_job_is_noop(tmp_path: Path):
    """terminal job 收到 cancel 时不应改写终态。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 terminal cancel", max_loops=2, research_profile="default", start_worker=False)
    service.store.update_job_status(job.job_id, status="completed", current_stage="completed")

    result = service.cancel(job.job_id)
    events = service.list_events(job.job_id)

    assert result.status == "completed"
    assert result.current_stage == "completed"
    assert result.cancel_requested is False
    assert not any(event.event_type == "job.cancel_requested" for event in events)


def test_job_service_retry_is_idempotent_for_same_source_job(tmp_path: Path):
    """重复 retry 同一个原 job 时，应返回已有直接 retry job。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 retry idempotency", max_loops=2, research_profile="default", start_worker=False)
    service.store.update_job_status(job.job_id, status="failed", current_stage="failed", error="测试失败")

    first = service.retry(job.job_id, start_worker=False)
    second = service.retry(job.job_id, start_worker=False)

    assert first.job_id == second.job_id
    assert first.retry_of == job.job_id
    assert second.attempt_index == 2


def test_recover_stale_jobs_skips_live_worker(tmp_path: Path, monkeypatch):
    """心跳新且 pid 存活时，不应触发 stale recovery。"""
    from deep_research_agent.research_jobs import service as service_module
    from services.research_jobs.service import ResearchJobService

    spawned: list[str] = []
    service = ResearchJobService(
        workspace_dir=str(tmp_path),
        spawn_worker_fn=spawned.append,
    )
    job = service.submit(topic="phase2 live recovery", max_loops=2, research_profile="default", start_worker=False)
    service.store.acquire_worker_lease(job.job_id, worker_pid=12345, lease_id="lease-live")
    monkeypatch.setattr(service_module, "_process_exists", lambda pid: True)

    recovered = service.recover_stale_jobs()

    assert recovered == []
    assert spawned == []
    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.worker_lease_id == "lease-live"


def test_recover_stale_jobs_skips_intentionally_idle_created_job(tmp_path: Path, monkeypatch):
    """显式 no-worker 的 created job 不应在下一条 CLI 命令里被自动拉起。"""
    from deep_research_agent.research_jobs import service as service_module
    from services.research_jobs.service import ResearchJobService

    spawned: list[str] = []
    service = ResearchJobService(
        workspace_dir=str(tmp_path),
        stale_timeout_seconds=1,
        spawn_worker_fn=spawned.append,
    )
    job = service.submit(topic="phase2 idle no-worker", max_loops=2, research_profile="default", start_worker=False)
    monkeypatch.setattr(service_module, "_process_exists", lambda pid: False)

    recovered = service.recover_stale_jobs()

    assert recovered == []
    assert spawned == []
    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.status == "created"
    assert loaded.current_stage == "clarifying"
    assert loaded.worker_pid is None
    assert loaded.worker_lease_id is None
    assert not any(event.event_type == "job.recovered" for event in service.list_events(job.job_id))


def test_recover_stale_jobs_clears_stale_lease_and_spawns_once(tmp_path: Path, monkeypatch):
    """陈旧 worker 应清理旧 lease 并触发一次恢复 spawn。"""
    from datetime import datetime, timedelta, timezone

    from deep_research_agent.research_jobs import service as service_module
    from services.research_jobs.service import ResearchJobService

    spawned: list[str] = []
    service = ResearchJobService(
        workspace_dir=str(tmp_path),
        stale_timeout_seconds=1,
        spawn_worker_fn=spawned.append,
    )
    job = service.submit(topic="phase2 stale recovery", max_loops=2, research_profile="default", start_worker=False)
    service.store.acquire_worker_lease(job.job_id, worker_pid=12345, lease_id="lease-stale")
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    service.store.update_job(job.job_id, last_heartbeat_at=stale_time)
    monkeypatch.setattr(service_module, "_process_exists", lambda pid: False)

    recovered = service.recover_stale_jobs()

    assert spawned == [job.job_id]
    assert len(recovered) == 1
    loaded = service.get(job.job_id)
    assert loaded is not None
    assert loaded.worker_lease_id is None
    assert loaded.active_checkpoint_id is not None
    assert any(event.event_type == "job.recovered" for event in service.list_events(job.job_id))


def test_completed_job_projection_keeps_active_checkpoint_explainable(tmp_path: Path):
    """完成后的 job row 应能对应 active checkpoint 的 terminal next_stage。"""
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase2 projection", max_loops=1, research_profile="default", start_worker=False)
    source = SourceRecord(
        citation_id=1,
        source_type="web",
        query="phase2 projection",
        title="Projection",
        url="https://example.com/projection",
        snippet="projection needs an active checkpoint",
        selected=True,
        trust_tier=4,
    )
    orchestrator = ResearchJobOrchestrator(
        service=service,
        planner_fn=lambda state: {
            "tasks": [TaskItem(id=1, title="投影", intent="验证", query="phase2 projection")],
            "status": "planned",
        },
        collect_step_fn=lambda state: (
            {
                "task_summaries": ["projection is explainable.[1]"],
                "sources_gathered": [source],
                "status": "researched",
            },
            False,
        ),
        verifier_fn=lambda state: {
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": state.get("memory_stats"),
            "run_metrics": state.get("run_metrics"),
            "status": "verified",
        },
        claim_auditor_fn=lambda state: {
            "audit_gate_status": "passed",
            "critical_claim_count": 0,
            "blocked_critical_claim_count": 0,
            "status": "claim_audited",
        },
        writer_fn=lambda state: {
            "final_report": "# 报告\n\nprojection is explainable.[1]",
            "report_artifact": ReportArtifact(
                topic=state["research_topic"],
                report="# 报告\n\nprojection is explainable.[1]",
                citations=[source],
                metrics=RunMetrics(status="completed"),
            ),
            "status": "completed",
        },
    )

    final_job = orchestrator.run(job.job_id)
    checkpoint = service.store.get_checkpoint(final_job.job_id, final_job.active_checkpoint_id or "")

    assert final_job.status == "completed"
    assert final_job.current_stage == "completed"
    assert checkpoint is not None
    assert checkpoint.next_stage == "completed"


def test_phase2_nodes_accept_checkpoint_serialized_payloads(tmp_path: Path, monkeypatch):
    """verifier / critic / writer 应接受 checkpoint 恢复后的 dict payload。"""
    from legacy.agents.critic import critic_node
    from legacy.agents.verifier import verifier_node
    from legacy.agents.writer import writer_node

    settings = type("Settings", (), {"workspace_dir": str(tmp_path / "workspace")})()
    monkeypatch.setattr("legacy.agents.verifier.get_settings", lambda: settings)

    source = SourceRecord(
        citation_id=1,
        source_type="web",
        query="phase2 checkpoint payload",
        title="可信深度研究 app",
        url="https://example.com/phase2",
        snippet="phase2 需要 job orchestrator。",
        selected=True,
        trust_tier=4,
    )
    note = EvidenceNote(
        task_id=1,
        task_title="验证 checkpoint",
        query="phase2 checkpoint payload",
        summary="phase2 需要 job orchestrator。[1]",
        source_ids=[1],
        selected_source_ids=[1],
    )
    task = TaskItem(
        id=1,
        title="验证 checkpoint",
        intent="验证序列化恢复",
        query="phase2 checkpoint payload",
        status="completed",
    )

    verifier_result = verifier_node(
        {
            "research_topic": "phase2 checkpoint payload",
            "ablation_variant": None,
            "sources_gathered": [source.model_dump(mode="json")],
            "evidence_notes": [note.model_dump(mode="json")],
            "run_metrics": RunMetrics().model_dump(mode="json"),
        }
    )
    critic_result = critic_node(
        {
            "research_topic": "phase2 checkpoint payload",
            "research_profile": "benchmark",
            "ablation_variant": None,
            "task_summaries": ["phase2 需要 job orchestrator。[1]"],
            "sources_gathered": [source.model_dump(mode="json")],
            "tasks": [task.model_dump(mode="json")],
            "memory_stats": verifier_result["memory_stats"],
            "loop_count": 0,
            "max_loops": 2,
            "run_metrics": RunMetrics().model_dump(mode="json"),
        }
    )
    writer_result = writer_node(
        {
            "research_topic": "phase2 checkpoint payload",
            "research_profile": "benchmark",
            "tasks": [task.model_dump(mode="json")],
            "task_summaries": ["phase2 需要 job orchestrator。[1]"],
            "sources_gathered": [source.model_dump(mode="json")],
            "evidence_notes": [note.model_dump(mode="json")],
            "evidence_units": verifier_result["evidence_units"],
            "evidence_clusters": verifier_result["evidence_clusters"],
            "verification_records": verifier_result["verification_records"],
            "memory_stats": verifier_result["memory_stats"],
            "run_metrics": RunMetrics().model_dump(mode="json"),
        }
    )

    assert verifier_result["status"] == "verified"
    assert critic_result["status"] == "reviewed"
    assert writer_result["status"] == "completed"
