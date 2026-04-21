"""Deterministic stage orchestration for research jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from loguru import logger

from deep_research_agent.auditor.pipeline import claim_auditor_node
from deep_research_agent.reporting.bundle import emit_report_artifacts
from legacy.agents.planner import planner_node
from legacy.agents.researcher import collect_research_step
from legacy.agents.verifier import verifier_node
from legacy.agents.writer import writer_node
from deep_research_agent.research_jobs.models import (
    TERMINAL_JOB_STATUSES,
    JobStatus,
    JobCheckpoint,
    JobProgressEvent,
    JobRuntimeRecord,
    RuntimeStage,
)
from legacy.workflows.states import CriticFeedback, ResearchState


def _default_synthesizer(_: dict[str, Any]) -> dict[str, Any]:
    """Keep the default local runtime smoke path provider-free."""

    return {}


class ResearchJobOrchestrator:
    """阶段性调度 research job。"""

    def __init__(
        self,
        *,
        service,
        planner_fn: Callable[[dict[str, Any]], dict[str, Any]] = planner_node,
        collect_step_fn: Callable[[dict[str, Any]], tuple[dict[str, Any], bool]] = collect_research_step,
        verifier_fn: Callable[[dict[str, Any]], dict[str, Any]] = verifier_node,
        critic_fn: Callable[[dict[str, Any]], dict[str, Any]] = _default_synthesizer,
        claim_auditor_fn: Callable[[dict[str, Any]], dict[str, Any]] = claim_auditor_node,
        writer_fn: Callable[[dict[str, Any]], dict[str, Any]] = writer_node,
        worker_lease_id: str | None = None,
    ) -> None:
        self.service = service
        self.store = service.store
        self.planner_fn = planner_fn
        self.collect_step_fn = collect_step_fn
        self.verifier_fn = verifier_fn
        self.critic_fn = critic_fn
        self.claim_auditor_fn = claim_auditor_fn
        self.writer_fn = writer_fn
        self.worker_lease_id = worker_lease_id

    def run(self, job_id: str) -> JobRuntimeRecord:
        """执行或恢复指定 job。"""
        job = self._assert_worker_lease(job_id)

        while job.status not in TERMINAL_JOB_STATUSES:
            job = self._assert_worker_lease(job_id)
            if job.cancel_requested:
                job = self._mark_cancelled(job, stage=job.current_stage)
                break

            stage = job.current_stage
            if job.status != JobStatus.RUNNING:
                job = self.store.update_job_status(job.job_id, status=JobStatus.RUNNING, current_stage=stage)
            state = self._load_state(job)
            self._append_event(job, stage.value, "stage.started", f"开始 {stage.value} 阶段")

            try:
                state, next_stage, terminal_status = self._run_stage(job, stage, state)
            except Exception as exc:
                logger.exception("Phase2 job 执行失败: job_id={}, stage={}", job_id, stage)
                job = self.store.update_job_status(
                    job_id,
                    status=JobStatus.FAILED,
                    current_stage=RuntimeStage.FAILED,
                    error=str(exc),
                )
                self._append_event(job, stage.value, "job.failed", f"{stage.value} 阶段失败", {"error": str(exc)})
                break

            checkpoint = self._save_checkpoint(job, stage=stage, next_stage=next_stage, state=state)
            job = self._sync_job_runtime_fields(job, state)
            self._append_event(
                job,
                stage,
                "stage.completed",
                f"{stage.value} 阶段完成",
                {"checkpoint_id": checkpoint.checkpoint_id, "next_stage": next_stage.value},
            )

            if terminal_status is not None:
                job = self.store.update_job_status(
                    job.job_id,
                    status=terminal_status,
                    current_stage=RuntimeStage(terminal_status.value),
                    active_checkpoint_id=checkpoint.checkpoint_id,
                )
                event_type = "job.completed" if terminal_status == JobStatus.COMPLETED else f"job.{terminal_status.value}"
                self._append_event(job, terminal_status.value, event_type, f"job 进入 {terminal_status.value}")
                if terminal_status == JobStatus.COMPLETED:
                    job = self._emit_job_artifacts(job, state)
                break

            job = self.store.update_job_status(
                job.job_id,
                status=JobStatus.RUNNING,
                current_stage=next_stage,
                active_checkpoint_id=checkpoint.checkpoint_id,
            )

        return self._require_job(job_id)

    def _run_stage(
        self,
        job: JobRuntimeRecord,
        stage: RuntimeStage,
        state: dict[str, Any],
    ) -> tuple[dict[str, Any], RuntimeStage, JobStatus | None]:
        if stage == RuntimeStage.CLARIFYING:
            merged = self._merge_state(state, {"status": RuntimeStage.CLARIFYING.value})
            return merged, RuntimeStage.PLANNED, None

        if stage == RuntimeStage.PLANNED:
            merged = self._merge_state(state, self.planner_fn(state))
            return merged, RuntimeStage.COLLECTING, None

        if stage == RuntimeStage.COLLECTING:
            merged_patch, has_more_work = self.collect_step_fn(state)
            merged = self._merge_state(state, merged_patch)
            next_stage = RuntimeStage.COLLECTING if has_more_work else RuntimeStage.NORMALIZING
            return merged, next_stage, None

        if stage == RuntimeStage.NORMALIZING:
            merged = self._merge_state(state, {"status": RuntimeStage.NORMALIZING.value})
            return merged, RuntimeStage.EXTRACTING, None

        if stage == RuntimeStage.EXTRACTING:
            merged = self._merge_state(state, self.verifier_fn(state))
            return merged, RuntimeStage.CLAIM_AUDITING, None

        if stage == RuntimeStage.CLAIM_AUDITING:
            merged = self._merge_state(state, self.claim_auditor_fn(state))
            gate_status = str(merged.get("audit_gate_status") or "unchecked")
            current_loop = int(merged.get("loop_count", 0))
            max_loops = int(merged.get("max_loops", 3))
            if gate_status == "passed":
                return merged, RuntimeStage.SYNTHESIZING, None
            if current_loop + 1 < max_loops:
                merged["loop_count"] = current_loop + 1
                merged["status"] = "needs_more_research"
                return self._merge_state(state, merged), RuntimeStage.COLLECTING, None
            return merged, RuntimeStage.SYNTHESIZING, None

        if stage == RuntimeStage.SYNTHESIZING:
            merged = self._merge_state(state, self.critic_fn(state))
            feedback = merged.get("critic_feedback")
            if feedback and not isinstance(feedback, CriticFeedback):
                feedback = CriticFeedback.model_validate(feedback)
                merged["critic_feedback"] = feedback
            pending_queries = list(getattr(feedback, "follow_up_queries", []) or [])
            merged["pending_follow_up_queries"] = pending_queries
            quality_gate_status = str(merged.get("quality_gate_status") or "")
            research_profile = str(merged.get("research_profile") or "default")
            current_loop = int(merged.get("loop_count", 0))
            max_loops = int(merged.get("max_loops", 3))
            if quality_gate_status == "failed" and research_profile == "benchmark":
                merged["status"] = "failed"
                return merged, RuntimeStage.FAILED, JobStatus.FAILED
            if feedback is not None and not feedback.is_sufficient and current_loop + 1 < max_loops:
                merged["loop_count"] = current_loop + 1
                return merged, RuntimeStage.COLLECTING, None
            return merged, RuntimeStage.RENDERING, None

        if stage == RuntimeStage.RENDERING:
            merged = self._merge_state(state, self.writer_fn(state))
            return merged, RuntimeStage.COMPLETED, JobStatus.COMPLETED

        raise ValueError(f"不支持的阶段: {stage}")

    def _require_job(self, job_id: str) -> JobRuntimeRecord:
        job = self.store.get_job(job_id)
        if job is None:
            raise KeyError(f"未知 job: {job_id}")
        return job

    def _assert_worker_lease(self, job_id: str) -> JobRuntimeRecord:
        if self.worker_lease_id is None:
            return self._require_job(job_id)
        return self.store.assert_worker_lease(job_id, lease_id=self.worker_lease_id)

    def _load_state(self, job: JobRuntimeRecord) -> dict[str, Any]:
        job_workspace_dir = str(self.store.job_dir(job.job_id))
        checkpoint_id = job.active_checkpoint_id
        checkpoint = self.store.get_checkpoint(job.job_id, checkpoint_id) if checkpoint_id else None
        if checkpoint is None:
            checkpoint = self.store.get_latest_checkpoint(job.job_id)
        if checkpoint is None:
            return self.service.build_initial_state(
                topic=job.topic,
                max_loops=int(job.metadata.get("max_loops", 3)),
                research_profile=str(job.metadata.get("research_profile", "default")),
                source_profile=job.source_profile,
                policy_overrides=dict(job.policy_overrides),
                file_inputs=[],
                job_workspace_dir=job_workspace_dir,
            )
        state = ResearchState.model_validate(checkpoint.state_payload).model_dump(mode="json")
        state["job_workspace_dir"] = job_workspace_dir
        return state

    def _merge_state(self, state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = dict(state)
        merged.update(patch)
        return ResearchState.model_validate(merged).model_dump(mode="json")

    def _sync_job_runtime_fields(self, job: JobRuntimeRecord, state: dict[str, Any]) -> JobRuntimeRecord:
        self._assert_worker_lease(job.job_id)
        return self.store.update_job(
            job.job_id,
            connector_health=dict(state.get("connector_health") or {}),
            audit_gate_status=str(state.get("audit_gate_status") or job.audit_gate_status),
            critical_claim_count=int(state.get("critical_claim_count", job.critical_claim_count)),
            blocked_critical_claim_count=int(
                state.get("blocked_critical_claim_count", job.blocked_critical_claim_count)
            ),
            audit_graph_path=str(state.get("audit_graph_path") or job.audit_graph_path),
            review_queue_path=str(state.get("review_queue_path") or job.review_queue_path),
        )

    def _save_checkpoint(
        self,
        job: JobRuntimeRecord,
        *,
        stage: RuntimeStage,
        next_stage: RuntimeStage,
        state: dict[str, Any],
    ) -> JobCheckpoint:
        self._assert_worker_lease(job.job_id)
        checkpoint = JobCheckpoint(
            checkpoint_id=f"{job.job_id}-checkpoint-pending",
            job_id=job.job_id,
            stage=stage,
            sequence=0,
            loop_count=int(state.get("loop_count", 0)),
            next_stage=next_stage,
            state_payload=state,
        )
        return self.store.save_checkpoint(checkpoint)

    def _append_event(
        self,
        job: JobRuntimeRecord,
        stage: str,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobProgressEvent:
        self._assert_worker_lease(job.job_id)
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

    def _mark_cancelled(self, job: JobRuntimeRecord, *, stage: RuntimeStage | str) -> JobRuntimeRecord:
        self._assert_worker_lease(job.job_id)
        cancelled = self.store.update_job_status(
            job.job_id,
            status=JobStatus.CANCELLED,
            current_stage=RuntimeStage.CANCELLED,
            cancel_requested=True,
        )
        stage_name = stage.value if hasattr(stage, "value") else stage
        self._append_event(cancelled, stage_name, "job.cancelled", "job 已取消")
        return cancelled

    def _emit_job_artifacts(self, job: JobRuntimeRecord, state: dict[str, Any]) -> JobRuntimeRecord:
        self._assert_worker_lease(job.job_id)
        report_text = str(state.get("final_report") or "")
        Path(job.report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(job.report_path).write_text(report_text, encoding="utf-8")

        self._append_event(
            job,
            "bundle",
            "bundle.emitted",
            "输出 report bundle 与 trace",
            {
                "report_path": job.report_path,
                "report_bundle_path": job.report_bundle_path,
                "trace_path": job.trace_path,
            },
        )

        state_for_artifacts = dict(state)
        if not state_for_artifacts.get("review_queue_path"):
            state_for_artifacts["review_queue_path"] = job.review_queue_path
        if not state_for_artifacts.get("audit_graph_path"):
            state_for_artifacts["audit_graph_path"] = job.audit_graph_path
        trace_events = [event.model_dump(mode="json") for event in self.store.list_events(job.job_id)]
        emit_report_artifacts(
            state_for_artifacts,
            topic=str(state_for_artifacts.get("research_topic") or job.topic),
            max_loops=int(job.metadata.get("max_loops", 3)),
            research_profile=str(job.metadata.get("research_profile", "default")),
            workspace_dir=self.store.job_dir(job.job_id),
            bundle_output_dirname="bundle",
            source_profile=job.source_profile,
            job_id=job.job_id,
            bundle_dir=self.store.bundle_dir(job.job_id),
            runtime_path=job.runtime_path,
            trace_events=trace_events,
            report_bundle_ref="bundle/report_bundle.json",
            report_path=Path(job.report_path),
        )
        return self.store.update_job(
            job.job_id,
            report_path=str(Path(job.report_path)),
            report_bundle_path=str(Path(job.report_bundle_path)),
            trace_path=str(Path(job.trace_path)),
        )
