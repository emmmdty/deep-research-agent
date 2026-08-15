"""Deterministic stage orchestration for research jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from loguru import logger

from deep_research_agent.auditor.pipeline import claim_auditor_node
from deep_research_agent.kernel.contracts import (
    CorpusManifest,
    ResearchGraph,
    ResearchGraphNode,
)
from deep_research_agent.orchestration.dag import ResearchDAG
from deep_research_agent.orchestration.events import FileRunJournal
from deep_research_agent.orchestration.scheduler import ResearchScheduler, RunResult
from deep_research_agent.reporting.bundle import emit_report_artifacts
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2
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
        scheduler: ResearchScheduler | None = None,
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
        self.scheduler = scheduler

    async def run_dag(
        self,
        job_id: str,
        dag: ResearchDAG,
        config_snapshot: Any,
    ) -> RunResult:
        """Run a new typed DAG while retaining ``run`` for legacy checkpoints."""

        if self.scheduler is None:
            raise RuntimeError("run_dag requires an injected ResearchScheduler")
        job = self._assert_worker_lease(job_id)
        job = self.store.update_job(
            job_id,
            lease_id=self.worker_lease_id,
            status=JobStatus.RUNNING,
            current_stage=RuntimeStage.COLLECTING,
            runtime_path="scheduler-v2",
            error=None,
        )
        journal = FileRunJournal(self.store.job_dir(job_id) / "scheduler_journal.jsonl")
        seed_checkpoints = journal.load_checkpoints()
        if seed_checkpoints:
            logger.info(
                "scheduler-v2 job {}: resuming from {} persisted task checkpoint(s)",
                job_id,
                len(seed_checkpoints),
            )
        result = await self.scheduler.run(
            job,
            dag,
            config_snapshot,
            seed_checkpoints=seed_checkpoints,
        )
        self._assert_worker_lease(job_id)

        journal_events, _ = journal.load()
        if journal_events:
            for event in journal_events:
                payload = dict(event.payload)
                payload.update(
                    {
                        "scheduler_sequence": event.sequence,
                        "task_id": event.task_id,
                        "attempt": event.attempt,
                    }
                )
                self._append_event(
                    job,
                    "scheduler",
                    event.event_type,
                    event.event_type,
                    payload,
                )
        merged_checkpoints = {cp.task_id: cp for cp in journal.load_checkpoints()}
        for checkpoint in result.checkpoints:
            merged_checkpoints[checkpoint.task_id] = checkpoint
        checkpoint_path = self.store.save_scheduler_checkpoints(
            job_id,
            [cp.model_dump(mode="json") for cp in merged_checkpoints.values()],
            lease_id=self.worker_lease_id,
        )

        status_by_result = {
            "completed": JobStatus.COMPLETED,
            "failed": JobStatus.FAILED,
            "cancelled": JobStatus.CANCELLED,
        }
        stage_by_result = {
            "completed": RuntimeStage.COMPLETED,
            "failed": RuntimeStage.FAILED,
            "cancelled": RuntimeStage.CANCELLED,
        }
        metadata = dict(job.metadata)
        metadata["scheduler_checkpoint_path"] = str(checkpoint_path)
        metadata["scheduler_config_snapshot"] = result.config_snapshot
        if result.status == "completed":
            self._emit_scheduler_bundle(job, dag, result)
        errors = [
            task_result.error
            for task_result in result.task_results.values()
            if task_result.status == "failed" and task_result.error
        ]
        updated = self.store.update_job(
            job_id,
            lease_id=self.worker_lease_id,
            status=status_by_result[result.status],
            current_stage=stage_by_result[result.status],
            cancel_requested=result.status == "cancelled",
            metadata=metadata,
            error=errors[0] if errors else None,
        )
        self._append_event(
            updated,
            stage_by_result[result.status],
            f"job.{result.status}",
            f"job entered {result.status}",
            {"terminal": True},
        )
        return result

    def _emit_scheduler_bundle(
        self,
        job: JobRuntimeRecord,
        dag: ResearchDAG,
        result: RunResult,
    ) -> None:
        packets = [
            packet
            for task_result in result.task_results.values()
            for packet in task_result.evidence_packets
        ]
        output_artifacts = [
            artifact
            for task_result in result.task_results.values()
            for artifact in task_result.output_artifacts
        ]
        packet_artifacts = [artifact for packet in packets for artifact in packet.artifacts]
        all_artifacts = [*packet_artifacts, *output_artifacts]
        frozen_manifest = job.metadata.get("corpus_manifest") or {}
        hashes: dict[str, str] = dict(frozen_manifest.get("content_hashes") or {})
        critical_claims_allowed: dict[str, bool] = dict(
            frozen_manifest.get("critical_claims_allowed") or {}
        )
        for artifact in all_artifacts:
            document_version_id = artifact.metadata.get("document_version_id")
            if not isinstance(document_version_id, str):
                continue
            existing = hashes.get(document_version_id)
            if existing is not None and existing != artifact.content_sha256:
                raise ValueError(
                    f"conflicting source hashes for document {document_version_id!r}"
                )
            hashes[document_version_id] = artifact.content_sha256
            artifact_allowed = bool(artifact.metadata.get("critical_claims_allowed", False))
            if document_version_id in critical_claims_allowed:
                critical_claims_allowed[document_version_id] = (
                    critical_claims_allowed[document_version_id] and artifact_allowed
                )
            else:
                critical_claims_allowed[document_version_id] = artifact_allowed

        manifest = CorpusManifest(
            manifest_id=f"{job.job_id}:corpus",
            document_version_ids=tuple(sorted(hashes)),
            content_hashes=hashes,
            critical_claims_allowed=critical_claims_allowed,
        )
        claims = [claim for packet in packets for claim in packet.claims]
        citation_verification: dict[str, Any] = {}
        if any(claim.critical for claim in claims):
            try:
                from deep_research_agent.auditor.citation_verifier import CitationVerifier

                document_contents = {
                    artifact.metadata["document_version_id"]: artifact.metadata["source_text"]
                    for artifact in all_artifacts
                    if isinstance(artifact.metadata.get("document_version_id"), str)
                    and isinstance(artifact.metadata.get("source_text"), str)
                }
                verifier = CitationVerifier()
                verification = verifier.verify(
                    claims,
                    all_artifacts,
                    document_contents=document_contents,
                    job_id=job.job_id,
                )
                citation_verification = verification.model_dump(mode="json")
                verifier.to_disk(verification, Path(job.report_bundle_path).parent)
            except Exception as exc:  # noqa: BLE001 - verification must not fail the job
                logger.warning(
                    "citation verification failed for job {}: {}",
                    job.job_id,
                    exc,
                )
                citation_verification = {}
        graph = self._scheduler_graph(result, claims)
        report_markdown = self._scheduler_report_markdown(job, result)
        task_by_id = dag.task_by_id
        tasks = []
        for task_id, task_result in sorted(result.task_results.items()):
            task = task_by_id[task_id]
            tasks.append(
                {
                    "task_id": task_id,
                    "task": task.objective,
                    "role": task.role,
                    "model": self._task_model(result.config_snapshot, task.role),
                    "state": task_result.status,
                    "retry": max(result.attempts.get(task_id, 1) - 1, 0),
                    "source_count": len(
                        {
                            span.document_version_id
                            for packet in task_result.evidence_packets
                            for span in packet.evidence_spans
                        }
                    ),
                }
            )
        bundle = ReportBundleCompilerV2().compile(
            report_markdown=report_markdown,
            claims=claims,
            evidence_packets=packets,
            critic_decisions=result.critic_decisions,
            research_graph=graph,
            sources=output_artifacts,
            corpus_manifest=manifest,
            run_manifest={
                "job_id": job.job_id,
                "runtime_path": "scheduler-v2",
                "config_version_id": job.metadata.get("product_config_version_id"),
                "tasks": tasks,
            },
            citation_verification=citation_verification,
        )
        bundle_path = Path(job.report_bundle_path)
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(
            ReportBundleCompilerV2.to_canonical_json(bundle),
            encoding="utf-8",
        )
        report_path = Path(job.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(bundle.report_markdown, encoding="utf-8")

    @staticmethod
    def _scheduler_report_markdown(job: JobRuntimeRecord, result: RunResult) -> str:
        for task_id in sorted(result.task_outputs, reverse=True):
            candidate = result.task_outputs[task_id].get("report_markdown")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip() + "\n"
        return (
            f"# {job.topic}\n\n"
            "## Executive Summary\n\n"
            "## Evidence Status\n\n"
            "No evidence-backed conclusion could be produced from the frozen corpus. "
            "No unsupported critical claim was published.\n"
        )

    @staticmethod
    def _scheduler_graph(result: RunResult, claims: list) -> ResearchGraph:
        for task_id in sorted(result.task_outputs, reverse=True):
            candidate = result.task_outputs[task_id].get("research_graph")
            if isinstance(candidate, dict):
                return ResearchGraph.model_validate(candidate)
        return ResearchGraph(
            nodes=[
                ResearchGraphNode(
                    node_id=claim.claim_id,
                    kind="claim",
                    label=claim.claim,
                    properties={"support_status": claim.support_status},
                )
                for claim in sorted(claims, key=lambda item: item.claim_id)
            ],
            edges=[],
        )

    @staticmethod
    def _task_model(config_snapshot: Any, role: str) -> str:
        if not isinstance(config_snapshot, dict):
            return "configured"
        return str(
            config_snapshot.get(f"{role}_endpoint_id")
            or config_snapshot.get("planner_endpoint_id")
            or config_snapshot.get("model")
            or "configured"
        )

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
        return self.store.save_checkpoint(checkpoint, lease_id=self.worker_lease_id)

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
        return self.store.append_event(event, lease_id=self.worker_lease_id)

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
