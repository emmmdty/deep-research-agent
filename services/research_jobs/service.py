"""Phase 02 research job service。"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from configs.settings import get_settings
from loguru import logger

from policies.models import SourcePolicyOverrides
from services.research_jobs.models import JobCheckpoint, JobProgressEvent, JobRuntimeRecord
from services.research_jobs.store import ResearchJobStore
from workflows.states import ResearchState


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
    """research job 提交、查询、取消、恢复入口。"""

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
            audit_gate_status="unchecked",
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
        current_stage: str = "clarifying",
    ) -> JobRuntimeRecord:
        """创建并可选启动一个新 job。"""
        job_id = _run_id()
        job_dir = self.store.job_dir(job_id)
        bundle_dir = self.store.bundle_dir(job_id)
        audit_dir = self.store.job_dir(job_id) / "audit"
        resolved_source_profile = source_profile or getattr(self.settings, "source_policy_mode", "open-web")
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
            status="created",
            current_stage=current_stage,
            attempt_index=attempt_index,
            retry_of=retry_of,
            report_path=str(job_dir / "report.md"),
            report_bundle_path=str(bundle_dir / "report_bundle.json"),
            trace_path=str(bundle_dir / "trace.jsonl"),
            source_profile=resolved_source_profile,
            budget=resolved_budget,
            policy_overrides=policy_overrides,
            connector_health={},
            audit_gate_status="unchecked",
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
            stage="created",
            sequence=1,
            loop_count=int(state_payload.get("loop_count", 0)),
            next_stage=current_stage,
            state_payload=ResearchState.model_validate(state_payload).model_dump(mode="json"),
        )
        self.store.save_checkpoint(checkpoint)
        job = self.store.update_job(job_id, active_checkpoint_id=checkpoint.checkpoint_id)

        if start_worker:
            self._spawn_worker_fn(job_id)
        return job

    def get(self, job_id: str) -> JobRuntimeRecord | None:
        return self.store.get_job(job_id)

    def list_events(self, job_id: str, *, after_sequence: int = 0) -> list[JobProgressEvent]:
        return self.store.list_events(job_id, after_sequence=after_sequence)

    def cancel(self, job_id: str) -> JobRuntimeRecord:
        self._require_job(job_id)
        updated = self.store.update_job(job_id, cancel_requested=True)
        self._append_event(updated, updated.current_stage, "job.cancel_requested", "收到取消请求")
        return updated

    def retry(self, job_id: str, *, start_worker: bool = True) -> JobRuntimeRecord:
        job = self._require_job(job_id)
        if job.status not in {"failed", "cancelled", "needs_review"}:
            raise ValueError(f"当前状态不允许 retry: {job.status}")
        checkpoint = self.store.get_latest_checkpoint(job_id)
        current_stage = checkpoint.next_stage if checkpoint is not None else "clarifying"
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
            current_stage=current_stage,
        )
        self._append_event(retry_job, "job", "job.retry_created", "由失败 job 派生 retry", {"retry_of": job.job_id})
        return retry_job

    def recover_stale_jobs(self) -> list[JobRuntimeRecord]:
        """扫描并恢复 stale job。"""
        recovered: list[JobRuntimeRecord] = []
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_timeout_seconds)
        for job in self.store.list_active_jobs():
            if job.last_heartbeat_at:
                heartbeat = datetime.fromisoformat(job.last_heartbeat_at)
                if heartbeat >= cutoff and _process_exists(job.worker_pid):
                    continue
            checkpoint = self.store.get_latest_checkpoint(job.job_id)
            if checkpoint is None:
                updated = self.store.update_job_status(
                    job.job_id,
                    status="needs_review",
                    current_stage="needs_review",
                    error="缺少可恢复 checkpoint",
                )
                self._append_event(updated, "job", "job.needs_review", "缺少可恢复 checkpoint")
                recovered.append(updated)
                continue
            self._append_event(job, "job", "job.recovered", "检测到 stale job，重新拉起 worker")
            self._spawn_worker_fn(job.job_id)
            recovered.append(self._require_job(job.job_id))
        return recovered

    def run_job(self, job_id: str):
        """在当前进程执行 job。"""
        from services.research_jobs.orchestrator import ResearchJobOrchestrator

        orchestrator = ResearchJobOrchestrator(service=self)
        return orchestrator.run(job_id)

    def _spawn_worker(self, job_id: str) -> subprocess.Popen:
        command = [
            sys.executable,
            "-m",
            "services.research_jobs.worker",
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
            cwd=Path(__file__).resolve().parent.parent.parent,
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
            event_id=f"{job.job_id}-event-{self.store.next_event_sequence(job.job_id):04d}",
            job_id=job.job_id,
            sequence=self.store.next_event_sequence(job.job_id),
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
