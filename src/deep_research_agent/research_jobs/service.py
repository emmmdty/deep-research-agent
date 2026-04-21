"""Canonical research-job service for the deterministic runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from configs.settings import get_settings
from deep_research_agent.common import DEFAULT_SOURCE_PROFILE, resolve_source_profile_name
from loguru import logger

from policies.models import SourcePolicyOverrides
from deep_research_agent.research_jobs.models import (
    REFINEMENT_SAFE_STAGE,
    TERMINAL_JOB_STATUSES,
    AuditGateStatus,
    JobCheckpoint,
    JobProgressEvent,
    JobRuntimeRecord,
    JobStatus,
    RuntimeStage,
    utc_now_iso,
)
from deep_research_agent.research_jobs.store import ResearchJobStore
from legacy.workflows.states import ResearchState


def _run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _process_exists(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class ResearchJobService:
    """Create, inspect, cancel, retry, resume, and refine research jobs."""

    def __init__(
        self,
        *,
        workspace_dir: str | None = None,
        runtime_dirname: str | None = None,
        heartbeat_interval_seconds: int | None = None,
        stale_timeout_seconds: int | None = None,
        settings=None,
        spawn_worker_fn=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.workspace_dir = workspace_dir or getattr(self.settings, "workspace_dir", "workspace")
        self.runtime_dirname = runtime_dirname or getattr(self.settings, "job_runtime_dirname", "research_jobs")
        self.heartbeat_interval_seconds = heartbeat_interval_seconds or int(
            getattr(self.settings, "job_heartbeat_interval_seconds", 2)
        )
        self.stale_timeout_seconds = stale_timeout_seconds or int(
            getattr(self.settings, "job_stale_timeout_seconds", 15)
        )
        self.store = ResearchJobStore(
            workspace_dir=self.workspace_dir,
            runtime_dirname=self.runtime_dirname,
        )
        self._spawn_worker_fn = spawn_worker_fn or self._spawn_worker

    def build_initial_state(
        self,
        *,
        topic: str,
        max_loops: int,
        research_profile: str,
        source_profile: str,
        policy_overrides: dict | None = None,
        file_inputs: list[str] | None = None,
        job_workspace_dir: str | None = None,
    ) -> dict:
        """构造可持久化的初始 ResearchState。"""
        return ResearchState(
            research_topic=topic,
            research_profile=research_profile,
            source_profile=source_profile,
            policy_overrides=policy_overrides or {},
            file_inputs=file_inputs or [],
            job_workspace_dir=job_workspace_dir or "",
            max_loops=max_loops,
            status="created",
            pending_follow_up_queries=[],
            source_snapshots=[],
            connector_health={},
            audit_gate_status=AuditGateStatus.UNCHECKED.value,
            audit_block_reason="",
            critical_claim_count=0,
            blocked_critical_claim_count=0,
        ).model_dump(mode="json")

    def submit(
        self,
        *,
        topic: str,
        max_loops: int,
        research_profile: str,
        start_worker: bool = True,
        source_profile: str | None = None,
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
        connector_budget: dict | None = None,
        file_inputs: list[str] | None = None,
        retry_of: str | None = None,
        attempt_index: int = 1,
        initial_state: dict | None = None,
        current_stage: str = RuntimeStage.CLARIFYING.value,
    ) -> JobRuntimeRecord:
        """Create a new job and optionally spawn a worker for it."""
        job_id = _run_id()
        job_dir = self.store.job_dir(job_id)
        bundle_dir = self.store.bundle_dir(job_id)
        audit_dir = self.store.job_dir(job_id) / "audit"
        resolved_source_profile = resolve_source_profile_name(
            source_profile or getattr(self.settings, "source_policy_mode", DEFAULT_SOURCE_PROFILE)
        )
        policy_overrides = SourcePolicyOverrides(
            allow_domains=allow_domains or [],
            deny_domains=deny_domains or [],
            budget=connector_budget,
        ).model_dump(mode="json", exclude_none=True)
        resolved_budget = dict(connector_budget or {})
        metadata = {
            "max_loops": max_loops,
            "research_profile": research_profile,
            "source_profile": resolved_source_profile,
            "input_prompt": topic,
        }
        job = JobRuntimeRecord(
            job_id=job_id,
            topic=topic,
            status=JobStatus.CREATED,
            current_stage=RuntimeStage(current_stage),
            attempt_index=attempt_index,
            retry_of=retry_of,
            report_path=str(job_dir / "report.md"),
            report_bundle_path=str(bundle_dir / "report_bundle.json"),
            trace_path=str(bundle_dir / "trace.jsonl"),
            source_profile=resolved_source_profile,
            budget=resolved_budget,
            policy_overrides=policy_overrides,
            connector_health={},
            audit_gate_status=AuditGateStatus.UNCHECKED,
            critical_claim_count=0,
            blocked_critical_claim_count=0,
            audit_graph_path=str(audit_dir / "claim_graph.json"),
            review_queue_path=str(audit_dir / "review_queue.json"),
            metadata=metadata,
        )
        self.store.upsert_job(job)
        self._append_event(job, "job", "job.created", "job 已创建", {"topic": topic, "research_profile": research_profile})

        state_payload = dict(initial_state or {})
        if not state_payload:
            state_payload = self.build_initial_state(
                topic=topic,
                max_loops=max_loops,
                research_profile=research_profile,
                source_profile=resolved_source_profile,
                policy_overrides=policy_overrides,
                file_inputs=file_inputs,
                job_workspace_dir=str(job_dir),
            )
        state_payload["job_workspace_dir"] = str(job_dir)
        state_payload["job_id"] = job_id
        checkpoint = JobCheckpoint(
            checkpoint_id=f"{job_id}-checkpoint-0001",
            job_id=job_id,
            stage=RuntimeStage.CREATED,
            sequence=1,
            loop_count=int(state_payload.get("loop_count", 0)),
            next_stage=RuntimeStage(current_stage),
            state_payload=ResearchState.model_validate(state_payload).model_dump(mode="json"),
        )
        checkpoint = self.store.save_checkpoint(checkpoint)
        job = self.store.update_job(job_id, active_checkpoint_id=checkpoint.checkpoint_id)

        if start_worker:
            self._spawn_worker_fn(job_id)
        return job

    def get(self, job_id: str) -> JobRuntimeRecord | None:
        return self.store.get_job(job_id)

    def list_events(self, job_id: str, *, after_sequence: int = 0) -> list[JobProgressEvent]:
        return self.store.list_events(job_id, after_sequence=after_sequence)

    def cancel(self, job_id: str) -> JobRuntimeRecord:
        job = self._require_job(job_id)
        if job.status in TERMINAL_JOB_STATUSES or job.cancel_requested:
            return job
        updated = self.store.update_job(job_id, cancel_requested=True)
        self._append_event(updated, updated.current_stage, "job.cancel_requested", "收到取消请求")
        if updated.status == JobStatus.CREATED and not updated.worker_lease_id and updated.worker_pid is None:
            updated = self.store.update_job_status(
                job_id,
                status=JobStatus.CANCELLED,
                current_stage=RuntimeStage.CANCELLED,
                cancel_requested=True,
            )
            self._append_event(updated, RuntimeStage.CANCELLED.value, "job.cancelled", "job 已取消")
        return updated

    def retry(self, job_id: str, *, start_worker: bool = True) -> JobRuntimeRecord:
        job = self._require_job(job_id)
        if job.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
            raise ValueError(f"当前状态不允许 retry: {job.status}")
        existing_retry = self.store.get_latest_retry(job.job_id)
        if existing_retry is not None:
            return existing_retry
        checkpoint = self.store.get_latest_checkpoint(job_id)
        current_stage = checkpoint.next_stage if checkpoint is not None else RuntimeStage.CLARIFYING
        initial_state = checkpoint.state_payload if checkpoint is not None else None
        retry_job = self.submit(
            topic=job.topic,
            max_loops=int(job.metadata.get("max_loops", 3)),
            research_profile=str(job.metadata.get("research_profile", "default")),
            start_worker=start_worker,
            source_profile=job.source_profile,
            allow_domains=list(job.policy_overrides.get("allow_domains", [])),
            deny_domains=list(job.policy_overrides.get("deny_domains", [])),
            connector_budget=dict(job.budget),
            file_inputs=list(initial_state.get("file_inputs", [])) if initial_state else None,
            retry_of=job.job_id,
            attempt_index=job.attempt_index + 1,
            initial_state=initial_state,
            current_stage=current_stage.value,
        )
        self._append_event(retry_job, "job", "job.retry_created", "由失败 job 派生 retry", {"retry_of": job.job_id})
        return retry_job

    def resume(self, job_id: str, *, start_worker: bool = True) -> JobRuntimeRecord:
        """Resume the same job from its latest checkpoint."""

        job = self._require_job(job_id)
        if job.status == JobStatus.COMPLETED:
            return job
        checkpoint = self._latest_checkpoint_or_raise(job_id)
        resumed = self.store.update_job_status(
            job_id,
            status=JobStatus.CREATED,
            current_stage=checkpoint.next_stage,
            cancel_requested=False,
            active_checkpoint_id=checkpoint.checkpoint_id,
        )
        resumed = self.store.update_job(job_id, error=None)
        self._append_event(
            resumed,
            checkpoint.next_stage.value,
            "job.resumed",
            "从最新 checkpoint 恢复 job",
            {"checkpoint_id": checkpoint.checkpoint_id},
        )
        if start_worker:
            self._spawn_worker_fn(job_id)
        return self._require_job(job_id)

    def refine(self, job_id: str, instruction: str, *, start_worker: bool = True) -> JobRuntimeRecord:
        """Record a refinement instruction and resume from a safe stage boundary."""

        checkpoint = self._latest_checkpoint_or_raise(job_id)
        state_payload = dict(checkpoint.state_payload)
        refinement_history = list(state_payload.get("refinement_history", []))
        refinement_history.append(
            {
                "instruction": instruction,
                "requested_at": utc_now_iso(),
            }
        )
        state_payload["refinement_history"] = refinement_history
        state_payload["pending_follow_up_queries"] = [instruction]
        state_payload["status"] = REFINEMENT_SAFE_STAGE.value
        state_payload["error"] = None

        refined_checkpoint = self.store.save_checkpoint(
            JobCheckpoint(
                checkpoint_id=f"{job_id}-checkpoint-pending",
                job_id=job_id,
                stage=checkpoint.stage,
                sequence=0,
                loop_count=int(state_payload.get("loop_count", checkpoint.loop_count)),
                next_stage=REFINEMENT_SAFE_STAGE,
                state_payload=ResearchState.model_validate(state_payload).model_dump(mode="json"),
            )
        )
        refined = self.store.update_job(
            job_id,
            status=JobStatus.CREATED,
            current_stage=REFINEMENT_SAFE_STAGE,
            cancel_requested=False,
            error=None,
            active_checkpoint_id=refined_checkpoint.checkpoint_id,
        )
        self._append_event(
            refined,
            REFINEMENT_SAFE_STAGE.value,
            "job.refine_requested",
            "记录 refinement 指令并重启到安全边界",
            {
                "instruction": instruction,
                "checkpoint_id": refined_checkpoint.checkpoint_id,
            },
        )
        if start_worker:
            self._spawn_worker_fn(job_id)
        return self._require_job(job_id)

    def record_review(
        self,
        job_id: str,
        *,
        review_item_id: str,
        claim_id: str,
        decision: str,
        reason: str,
        reviewer: str,
    ) -> JobRuntimeRecord:
        """Persist one append-only review action for a completed or blocked job."""

        if decision not in {"approve", "downgrade", "reject", "override"}:
            raise ValueError(f"unsupported review decision: {decision}")
        job = self._require_job(job_id)
        review_action = {
            "review_item_id": review_item_id,
            "claim_id": claim_id,
            "decision": decision,
            "reason": reason,
            "reviewer": reviewer,
            "created_at": utc_now_iso(),
        }
        audit_dir = Path(job.review_queue_path).parent
        audit_dir.mkdir(parents=True, exist_ok=True)
        actions_path = audit_dir / "review_actions.jsonl"
        with actions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(review_action, ensure_ascii=False) + "\n")

        metadata = dict(job.metadata)
        metadata["review_actions_path"] = str(actions_path)
        metadata["latest_review_action"] = review_action
        if decision in {"approve", "override"}:
            gate_status = AuditGateStatus.PASSED
        elif decision == "reject":
            gate_status = AuditGateStatus.BLOCKED
        else:
            gate_status = AuditGateStatus.PENDING_MANUAL_REVIEW

        updated = self.store.update_job(
            job_id,
            audit_gate_status=gate_status,
            metadata=metadata,
        )
        self._append_event(
            updated,
            "review",
            "job.review_recorded",
            "记录人工 review 动作",
            review_action,
        )
        self._append_review_trace(updated, review_action)
        self._update_audit_decision(updated, review_action)
        return self._require_job(job_id)

    def recover_stale_jobs(self) -> list[JobRuntimeRecord]:
        """Detect stale workers and restore resumable jobs."""
        recovered: list[JobRuntimeRecord] = []
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_timeout_seconds)
        for job in self.store.list_active_jobs():
            if (
                job.status == JobStatus.CREATED
                and job.worker_lease_id is None
                and job.worker_pid is None
                and job.last_heartbeat_at is None
            ):
                continue
            if job.last_heartbeat_at:
                heartbeat = datetime.fromisoformat(job.last_heartbeat_at)
                if heartbeat >= cutoff and _process_exists(job.worker_pid):
                    continue
            checkpoint = self.store.get_latest_checkpoint(job.job_id)
            if checkpoint is None:
                updated = self.store.update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    current_stage=RuntimeStage.FAILED,
                    error="缺少可恢复 checkpoint",
                    audit_gate_status=AuditGateStatus.PENDING_MANUAL_REVIEW,
                )
                self._append_event(updated, RuntimeStage.FAILED.value, "job.failed", "缺少可恢复 checkpoint")
                recovered.append(updated)
                continue
            if job.worker_lease_id:
                self.store.clear_worker(job.job_id, lease_id=job.worker_lease_id)
            updated = self.store.update_job(
                job.job_id,
                status=JobStatus.CREATED,
                current_stage=checkpoint.next_stage,
                cancel_requested=False,
                error=None,
                active_checkpoint_id=checkpoint.checkpoint_id,
            )
            self._append_event(
                updated,
                checkpoint.next_stage.value,
                "job.recovered",
                "检测到 stale job，重新拉起 worker",
                {"checkpoint_id": checkpoint.checkpoint_id},
            )
            self._spawn_worker_fn(job.job_id)
            recovered.append(self._require_job(job.job_id))
        return recovered

    def run_job(self, job_id: str, *, worker_lease_id: str | None = None):
        """在当前进程执行 job。"""
        from deep_research_agent.research_jobs.orchestrator import ResearchJobOrchestrator

        orchestrator = ResearchJobOrchestrator(service=self, worker_lease_id=worker_lease_id)
        return orchestrator.run(job_id)

    def _spawn_worker(self, job_id: str) -> subprocess.Popen:
        command = [
            sys.executable,
            "-m",
            "deep_research_agent.research_jobs.worker",
            "--job-id",
            job_id,
            "--workspace-dir",
            self.workspace_dir,
            "--runtime-dirname",
            self.runtime_dirname,
            "--heartbeat-interval-seconds",
            str(self.heartbeat_interval_seconds),
            "--stale-timeout-seconds",
            str(self.stale_timeout_seconds),
        ]
        logger.info("启动 phase2 worker: {}", " ".join(command))
        return subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[3],
            start_new_session=True,
        )

    def _append_event(
        self,
        job: JobRuntimeRecord,
        stage: str,
        event_type: str,
        message: str,
        payload: dict | None = None,
    ) -> JobProgressEvent:
        event = JobProgressEvent(
            event_id=f"{job.job_id}-event-pending",
            job_id=job.job_id,
            sequence=0,
            stage=stage,
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
        return self.store.append_event(event)

    def _require_job(self, job_id: str) -> JobRuntimeRecord:
        job = self.store.get_job(job_id)
        if job is None:
            raise KeyError(f"未知 job: {job_id}")
        return job

    def _latest_checkpoint_or_raise(self, job_id: str) -> JobCheckpoint:
        checkpoint = self.store.get_latest_checkpoint(job_id)
        if checkpoint is None:
            raise ValueError(f"job {job_id} 缺少可恢复 checkpoint")
        return checkpoint

    def _append_review_trace(self, job: JobRuntimeRecord, review_action: dict) -> None:
        trace_path = Path(job.trace_path)
        if not trace_path.exists():
            return
        entry = {
            "event_id": f"{job.job_id}-manual-review",
            "stage": "review",
            "event_type": "manual.review_recorded",
            "timestamp": review_action["created_at"],
            "payload": review_action,
        }
        with trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _update_audit_decision(self, job: JobRuntimeRecord, review_action: dict) -> None:
        audit_decision_path = Path(job.report_bundle_path).parent / "audit_decision.json"
        if not audit_decision_path.exists():
            return
        payload = json.loads(audit_decision_path.read_text(encoding="utf-8"))
        payload["gate_status"] = str(job.audit_gate_status)
        payload.setdefault("manual_reviews", []).append(review_action)
        audit_decision_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
