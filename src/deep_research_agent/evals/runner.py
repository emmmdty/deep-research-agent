"""Deterministic local eval runner for Phase 05."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from deep_research_agent.auditor.models import ClaimReviewQueue
from deep_research_agent.connectors.files import LocalFileIngestor as CanonicalLocalFileIngestor
from deep_research_agent.connectors.models import ConnectorFetchResult
from deep_research_agent.evals.contracts import (
    EVAL_SUITE_NAMES,
    EvalClaimSpec,
    EvalDataset,
    EvalEdgeSpec,
    EvalSourceSpec,
    EvalSuiteDefinition,
    EvalTaskSpec,
)
from deep_research_agent.research_jobs import ResearchJobOrchestrator, ResearchJobService
from legacy.workflows.states import CriticFeedback, ReportArtifact, RunMetrics, SourceRecord, TaskItem
from policies import load_source_policy


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUITES_ROOT = PROJECT_ROOT / "evals" / "suites"
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "evals" / "reports"
SUPPORTED_CLAIM_STATUSES = {"supported", "partially_supported"}
BLOCKING_CLAIM_STATUSES = {"unsupported", "unverifiable", "contradicted"}
FROZEN_ARTIFACT_TIMESTAMP = "2026-04-21T00:00:00+00:00"
RESEARCH_METRIC_ORDER = (
    "completion_rate",
    "bundle_emission_rate",
    "audit_pass_rate",
    "critical_claim_support_precision",
    "citation_error_rate",
    "provenance_completeness",
    "rubric_coverage",
    "policy_compliance_rate",
    "file_input_success_rate",
    "conflict_detection_recall",
)


def run_eval_suite(*, suite_name: str, output_root: str | Path | None = None) -> dict[str, Any]:
    """Run one deterministic local eval suite and persist its summary."""

    if suite_name not in EVAL_SUITE_NAMES:
        raise ValueError(f"unsupported eval suite: {suite_name}")
    suite = _load_suite_definition(suite_name)
    dataset = _load_dataset(suite)
    suite_output_root = Path(output_root or DEFAULT_REPORTS_ROOT / suite_name).resolve()
    suite_output_root.mkdir(parents=True, exist_ok=True)

    if suite.executor == "reliability_fixture":
        result = _run_reliability_suite(suite, dataset, suite_output_root)
    else:
        result = _run_research_fixture_suite(suite, dataset, suite_output_root)

    summary_path = suite_output_root / "summary.json"
    results_markdown_path = suite_output_root / "RESULTS.md"
    result["summary_path"] = _display_path(summary_path)
    result["results_markdown_path"] = _display_path(results_markdown_path)
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    results_markdown_path.write_text(_render_suite_markdown(result), encoding="utf-8")
    return result


def _load_suite_definition(suite_name: str) -> EvalSuiteDefinition:
    path = SUITES_ROOT / f"{suite_name}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EvalSuiteDefinition.model_validate(payload)


def _load_dataset(suite: EvalSuiteDefinition) -> EvalDataset:
    if suite.dataset_path is None:
        return EvalDataset()
    path = (PROJECT_ROOT / suite.dataset_path).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EvalDataset.model_validate(payload)


def _run_research_fixture_suite(
    suite: EvalSuiteDefinition,
    dataset: EvalDataset,
    suite_output_root: Path,
) -> dict[str, Any]:
    task_results = [_run_research_task(task, suite_output_root / task.task_id) for task in dataset.tasks]
    metrics = _aggregate_research_metrics(task_results)
    threshold_results = _evaluate_thresholds(metrics, suite.thresholds)
    status = "passed" if all(item["passed"] for item in threshold_results.values()) else "failed"
    return {
        "suite_name": suite.suite_name,
        "description": suite.description,
        "variant": dataset.variant,
        "status": status,
        "task_count": len(task_results),
        "metrics": metrics,
        "threshold_results": threshold_results,
        "rubric_path": suite.rubric_path,
        "tasks": task_results,
    }


def _run_research_task(task: EvalTaskSpec, task_output_root: Path) -> dict[str, Any]:
    task_output_root.mkdir(parents=True, exist_ok=True)
    workspace_dir = task_output_root / "workspace"
    ingested_sources, ingested_evidence = _ingest_task_files(task)
    public_sources = [_source_record(spec) for spec in task.sources]
    all_sources = public_sources + ingested_sources
    evidence_fragments = _resolve_evidence_fragments(task, all_sources, ingested_evidence)
    claims = _resolve_claims(task, evidence_fragments, all_sources)
    claim_support_edges = _resolve_claim_support_edges(task, claims, evidence_fragments, all_sources)
    conflict_sets = _resolve_conflict_sets(task)

    service = ResearchJobService(workspace_dir=str(workspace_dir))
    job = service.submit(
        topic=task.topic,
        max_loops=1,
        research_profile=task.research_profile,
        start_worker=False,
        source_profile=task.source_profile,
        allow_domains=task.allow_domains,
        deny_domains=task.deny_domains,
        file_inputs=[str((PROJECT_ROOT / path).resolve()) for path in task.file_inputs],
    )

    def planner_fn(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "tasks": [
                TaskItem(
                    id=index,
                    title=f"{task.task_id}-{index}",
                    intent=question,
                    query=question,
                    status="completed",
                    summary=question,
                    sources="[1]",
                )
                for index, question in enumerate(task.required_questions or [task.topic], start=1)
            ],
            "status": "planned",
        }

    def collect_step_fn(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        return (
            {
                "sources_gathered": all_sources,
                "source_snapshots": [],
                "evidence_notes": [
                    {
                        "task_id": index,
                        "task_title": question,
                        "query": question,
                        "summary": task.task_summaries[index - 1] if index - 1 < len(task.task_summaries) else question,
                        "source_ids": [source.citation_id for source in all_sources if source.selected],
                        "selected_source_ids": [source.citation_id for source in all_sources if source.selected],
                    }
                    for index, question in enumerate(task.answered_questions or task.required_questions or [task.topic], start=1)
                ],
                "task_summaries": task.task_summaries or [task.report_markdown.splitlines()[2].strip()],
                "status": "researched",
            },
            False,
        )

    def verifier_fn(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_fragments": evidence_fragments,
            "status": "verified",
        }

    def claim_auditor_fn(state: dict[str, Any]) -> dict[str, Any]:
        audit_paths = _write_audit_artifacts(
            job_workspace_dir=Path(str(state.get("job_workspace_dir") or "")),
            job_id=job.job_id,
            claims=claims,
            claim_support_edges=claim_support_edges,
            conflict_sets=conflict_sets,
        )
        return {
            "claims": claims,
            "claim_support_edges": claim_support_edges,
            "conflict_sets": conflict_sets,
            "audit_gate_status": "passed",
            "critical_claim_count": len([claim for claim in claims if claim["criticality"] == "high"]),
            "blocked_critical_claim_count": 0,
            "audit_graph_path": str(audit_paths["claim_graph_path"]),
            "review_queue_path": str(audit_paths["review_queue_path"]),
            "status": "audited",
        }

    def critic_fn(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "critic_feedback": CriticFeedback(
                quality_score=9,
                is_sufficient=True,
                gaps=[],
                follow_up_queries=[],
                feedback="Local eval smoke passed.",
            ),
            "loop_count": 0,
            "run_metrics": RunMetrics(
                time_seconds=1.0,
                llm_calls=0,
                search_calls=0,
                status="completed",
                selected_sources=len(all_sources),
            ),
            "status": "reviewed",
        }

    def writer_fn(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "final_report": task.report_markdown,
            "report_artifact": ReportArtifact(
                topic=task.topic,
                report=task.report_markdown,
                citations=all_sources,
                evidence_fragments=evidence_fragments,
                claims=claims,
                claim_support_edges=claim_support_edges,
                conflict_sets=conflict_sets,
                audit_gate_status="passed",
                metrics=RunMetrics(
                    time_seconds=1.0,
                    llm_calls=0,
                    search_calls=0,
                    status="completed",
                    selected_sources=len(all_sources),
                ),
            ),
            "status": "completed",
        }

    final_job = ResearchJobOrchestrator(
        service=service,
        planner_fn=planner_fn,
        collect_step_fn=collect_step_fn,
        verifier_fn=verifier_fn,
        critic_fn=critic_fn,
        claim_auditor_fn=claim_auditor_fn,
        writer_fn=writer_fn,
    ).run(job.job_id)

    stable_paths = _copy_task_artifacts(final_job, task_output_root)
    _normalize_task_artifacts(task, stable_paths)
    shutil.rmtree(task_output_root / "workspace", ignore_errors=True)
    bundle = json.loads(stable_paths["bundle_path"].read_text(encoding="utf-8"))
    task_metrics = _compute_research_task_metrics(task, bundle, all_sources, file_input_count=len(task.file_inputs))
    return {
        "task_id": task.task_id,
        "job_id": task.task_id,
        "status": final_job.status,
        "audit_gate_status": getattr(final_job.audit_gate_status, "value", str(final_job.audit_gate_status)),
        "report_path": _display_path(stable_paths["report_path"]),
        "bundle_path": _display_path(stable_paths["bundle_path"]),
        "manifest_path": _display_path(stable_paths["manifest_path"]),
        "task_metrics": task_metrics,
    }


def _run_reliability_suite(
    suite: EvalSuiteDefinition,
    dataset: EvalDataset,
    suite_output_root: Path,
) -> dict[str, Any]:
    workspace_dir = suite_output_root / "workspace"
    spawned_jobs: list[str] = []
    service = ResearchJobService(
        workspace_dir=str(workspace_dir),
        spawn_worker_fn=lambda job_id: spawned_jobs.append(job_id),
    )
    scenarios = {}

    created = service.submit(topic="cancel scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    cancelled = service.cancel(created.job_id)
    scenarios["cancel_created_job"] = cancelled.status == "cancelled"

    retried_base = service.submit(topic="retry scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    service.store.update_job_status(retried_base.job_id, status="failed", current_stage="failed", error="boom")
    retried = service.retry(retried_base.job_id, start_worker=False)
    scenarios["retry_failed_job"] = retried.retry_of == retried_base.job_id and retried.attempt_index == 2

    resumed_base = service.submit(topic="resume scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    service.store.update_job_status(resumed_base.job_id, status="failed", current_stage="failed", error="boom")
    resumed = service.resume(resumed_base.job_id, start_worker=False)
    scenarios["resume_failed_job"] = resumed.job_id == resumed_base.job_id and resumed.status == "created"

    refined_base = service.submit(topic="refine scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    service.store.update_job_status(refined_base.job_id, status="failed", current_stage="failed", error="boom")
    refined = service.refine(refined_base.job_id, "Expand the evidence map.", start_worker=False)
    scenarios["refine_failed_job"] = refined.current_stage == "planned"

    stale_job = service.submit(topic="stale recovery scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    service.store.update_job_status(stale_job.job_id, status="running", current_stage="collecting")
    service.store.acquire_worker_lease(stale_job.job_id, worker_pid=43210, lease_id="lease-stale")
    stale_heartbeat = (datetime.now(timezone.utc) - timedelta(seconds=3600)).isoformat()
    service.store.update_job(stale_job.job_id, last_heartbeat_at=stale_heartbeat)
    recovered_jobs = service.recover_stale_jobs()
    scenarios["stale_recovery"] = any(item.job_id == stale_job.job_id for item in recovered_jobs) and stale_job.job_id in spawned_jobs

    idle_job = service.submit(topic="idle noop scenario", max_loops=1, research_profile="eval_smoke", start_worker=False)
    idle_recovered = service.recover_stale_jobs()
    scenarios["idle_created_noop"] = all(item.job_id != idle_job.job_id for item in idle_recovered)

    scenario_order = dataset.scenarios or list(scenarios)
    ordered_results = [
        {"scenario_id": scenario_id, "passed": bool(scenarios.get(scenario_id, False))}
        for scenario_id in scenario_order
    ]
    metrics = {
        "completion_rate": _scenario_rate(ordered_results),
        "cancel_success_rate": _scenario_rate(ordered_results, "cancel_created_job"),
        "retry_success_rate": _scenario_rate(ordered_results, "retry_failed_job"),
        "resume_success_rate": _scenario_rate(ordered_results, "resume_failed_job"),
        "refine_success_rate": _scenario_rate(ordered_results, "refine_failed_job"),
        "stale_recovery_success_rate": _scenario_rate(ordered_results, "stale_recovery"),
        "idle_skip_rate": _scenario_rate(ordered_results, "idle_created_noop"),
    }
    shutil.rmtree(workspace_dir, ignore_errors=True)
    threshold_results = _evaluate_thresholds(metrics, suite.thresholds)
    status = "passed" if all(item["passed"] for item in threshold_results.values()) else "failed"
    return {
        "suite_name": suite.suite_name,
        "description": suite.description,
        "variant": dataset.variant,
        "status": status,
        "task_count": len(ordered_results),
        "metrics": metrics,
        "threshold_results": threshold_results,
        "rubric_path": suite.rubric_path,
        "tasks": ordered_results,
    }


def _scenario_rate(results: list[dict[str, Any]], scenario_id: str | None = None) -> float:
    filtered = [item for item in results if scenario_id is None or item["scenario_id"] == scenario_id]
    if not filtered:
        return 1.0
    return round(sum(1 for item in filtered if item["passed"]) / len(filtered), 3)


def _aggregate_research_metrics(task_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not task_results:
        return {
            "completion_rate": 0.0,
            "bundle_emission_rate": 0.0,
            "audit_pass_rate": 0.0,
            "critical_claim_support_precision": 0.0,
            "citation_error_rate": 1.0,
            "provenance_completeness": 0.0,
            "rubric_coverage": 0.0,
            "policy_compliance_rate": 0.0,
            "file_input_success_rate": 1.0,
            "conflict_detection_recall": 1.0,
        }
    aggregate: dict[str, float] = {}
    metric_names = {
        metric_name
        for task_result in task_results
        for metric_name in task_result["task_metrics"]
    }
    ordered_metric_names = [
        metric_name for metric_name in RESEARCH_METRIC_ORDER if metric_name in metric_names
    ] + sorted(metric_names.difference(RESEARCH_METRIC_ORDER))
    for task_result in task_results:
        metric_names.update(task_result["task_metrics"])
    for metric_name in ordered_metric_names:
        values = [float(task_result["task_metrics"].get(metric_name, 1.0)) for task_result in task_results]
        aggregate[metric_name] = round(sum(values) / len(values), 3)
    aggregate.setdefault("completion_rate", 0.0)
    aggregate.setdefault("bundle_emission_rate", 0.0)
    aggregate.setdefault("audit_pass_rate", 0.0)
    aggregate.setdefault("policy_compliance_rate", 1.0)
    aggregate.setdefault("file_input_success_rate", 1.0)
    aggregate.setdefault("conflict_detection_recall", 1.0)
    return aggregate


def _evaluate_thresholds(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for metric_name, threshold in thresholds.items():
        value = float(metrics.get(metric_name, 0.0))
        passed = True
        reason_parts: list[str] = []
        if threshold.min is not None and value < threshold.min:
            passed = False
            reason_parts.append(f"{value} < min {threshold.min}")
        if threshold.max is not None and value > threshold.max:
            passed = False
            reason_parts.append(f"{value} > max {threshold.max}")
        results[metric_name] = {
            "value": value,
            "min": threshold.min,
            "max": threshold.max,
            "passed": passed,
            "reason": "; ".join(reason_parts),
        }
    return results


def _render_suite_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['suite_name']}",
        "",
        f"- status: `{result['status']}`",
        f"- variant: `{result['variant']}`",
        f"- task_count: `{result['task_count']}`",
        "",
        "## Metrics",
        "",
    ]
    for metric_name, value in sorted((result.get("metrics") or {}).items()):
        lines.append(f"- {metric_name}: `{value}`")
    lines.extend(["", "## Thresholds", ""])
    for metric_name, payload in sorted((result.get("threshold_results") or {}).items()):
        lines.append(
            f"- {metric_name}: `{payload['passed']}` (value={payload['value']}, min={payload['min']}, max={payload['max']})"
        )
    lines.extend(["", "## Tasks", ""])
    for task in result.get("tasks", []):
        lines.append(f"- {task.get('task_id') or task.get('scenario_id')}: `{task.get('status', task.get('passed'))}`")
    lines.append("")
    return "\n".join(lines)


def _repo_relative_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _repo_scoped_uri(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_uri()
    return f"repo:///{relative}"


def _normalize_file_fetch_result(fetch_result: ConnectorFetchResult, *, file_path: Path) -> ConnectorFetchResult:
    relative_path = _repo_relative_path(file_path)
    stable_uri = _repo_scoped_uri(file_path)
    freshness_metadata = dict(fetch_result.freshness_metadata)
    freshness_metadata["file_path"] = relative_path
    metadata = dict(fetch_result.metadata)
    metadata["file_path"] = relative_path
    return fetch_result.model_copy(
        update={
            "canonical_uri": stable_uri,
            "url": stable_uri,
            "freshness_metadata": freshness_metadata,
            "metadata": metadata,
        }
    )


def _ingest_task_files(task: EvalTaskSpec) -> tuple[list[SourceRecord], list[dict[str, Any]]]:
    sources: list[SourceRecord] = []
    evidence: list[dict[str, Any]] = []
    ingestor = CanonicalLocalFileIngestor()
    starting_citation = len(task.sources)
    for offset, relative_path in enumerate(task.file_inputs, start=1):
        file_path = (PROJECT_ROOT / relative_path).resolve()
        fetch_result = _normalize_file_fetch_result(
            ingestor.ingest(str(file_path), query=task.topic),
            file_path=file_path,
        )
        stable_file_path = _repo_relative_path(file_path)
        citation_id = starting_citation + offset
        source_id = f"{task.task_id}-file-{offset}"
        snapshot_id = f"{task.task_id}-file-snapshot-{offset}"
        sources.append(_source_record_from_fetch(fetch_result, citation_id=citation_id, source_id=source_id, snapshot_id=snapshot_id))
        evidence.append(
            {
                "evidence_id": f"{task.task_id}-file-evidence-{offset}",
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "excerpt": fetch_result.text[:400],
                "locator": {"kind": "file_excerpt", "path": stable_file_path},
                "extraction_method": "local_file_ingest",
            }
        )
    return sources, evidence


def _source_record(spec: EvalSourceSpec) -> SourceRecord:
    payload = spec.model_dump(mode="json")
    return SourceRecord.model_validate(payload)


def _source_record_from_fetch(
    fetch_result: ConnectorFetchResult,
    *,
    citation_id: int,
    source_id: str,
    snapshot_id: str,
) -> SourceRecord:
    return SourceRecord(
        citation_id=citation_id,
        source_id=source_id,
        source_type=fetch_result.source_type,
        query=fetch_result.query,
        title=fetch_result.title,
        canonical_uri=fetch_result.canonical_uri,
        url=fetch_result.url,
        snippet=fetch_result.snippet,
        snapshot_ref=snapshot_id,
        mime_type=fetch_result.mime_type,
        auth_scope=fetch_result.auth_scope,
        freshness_metadata=fetch_result.freshness_metadata,
        metadata=fetch_result.metadata,
        trust_tier=5,
        selected=True,
    )


def _resolve_evidence_fragments(
    task: EvalTaskSpec,
    sources: list[SourceRecord],
    ingested_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if task.evidence_fragments:
        return [item.model_dump(mode="json") for item in task.evidence_fragments]
    evidence = list(ingested_evidence)
    if evidence:
        next_index = len(evidence) + 1
    else:
        next_index = 1
    for source in sources:
        if any(item["source_id"] == source.source_id for item in evidence):
            continue
        evidence.append(
            {
                "evidence_id": f"{task.task_id}-evidence-{next_index}",
                "source_id": source.source_id,
                "snapshot_id": source.snapshot_ref or f"{task.task_id}-snapshot-{next_index}",
                "excerpt": source.snippet or source.title,
                "locator": {"kind": "source_snippet", "citation_id": source.citation_id},
                "extraction_method": "fixture_source_snippet",
            }
        )
        next_index += 1
    return evidence


def _resolve_claims(
    task: EvalTaskSpec,
    evidence_fragments: list[dict[str, Any]],
    sources: list[SourceRecord],
) -> list[dict[str, Any]]:
    if task.claims:
        return [item.model_dump(mode="json") for item in task.claims]
    evidence_ids = [item["evidence_id"] for item in evidence_fragments]
    claim_text = _first_claim_text(task.report_markdown, task.topic)
    return [
        EvalClaimSpec(
            claim_id=f"{task.task_id}-claim-1",
            text=claim_text,
            criticality="high",
            uncertainty="low",
            status="supported",
            section_ref="Overview",
            evidence_ids=evidence_ids,
        ).model_dump(mode="json")
    ]


def _resolve_claim_support_edges(
    task: EvalTaskSpec,
    claims: list[dict[str, Any]],
    evidence_fragments: list[dict[str, Any]],
    sources: list[SourceRecord],
) -> list[dict[str, Any]]:
    if task.claim_support_edges:
        return [item.model_dump(mode="json") for item in task.claim_support_edges]
    source_by_id = {source.source_id: source for source in sources}
    claim_id = str(claims[0]["claim_id"])
    edges = []
    for index, evidence in enumerate(evidence_fragments, start=1):
        source = source_by_id.get(str(evidence["source_id"]))
        edges.append(
            EvalEdgeSpec(
                edge_id=f"{task.task_id}-edge-{index}",
                claim_id=claim_id,
                evidence_id=str(evidence["evidence_id"]),
                source_id=str(evidence["source_id"]),
                snapshot_id=str(evidence["snapshot_id"]),
                locator=dict(evidence.get("locator") or {}),
                relation="supports",
                confidence=0.99,
                grounding_status="grounded",
                notes=source.title if source is not None else "",
            ).model_dump(mode="json")
        )
    return edges


def _resolve_conflict_sets(task: EvalTaskSpec) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in task.conflict_sets]


def _write_audit_artifacts(
    *,
    job_workspace_dir: Path,
    job_id: str,
    claims: list[dict[str, Any]],
    claim_support_edges: list[dict[str, Any]],
    conflict_sets: list[dict[str, Any]],
) -> dict[str, Path]:
    audit_dir = job_workspace_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    claim_graph_path = audit_dir / "claim_graph.json"
    review_queue_path = audit_dir / "review_queue.json"
    claim_graph_path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "claims": claims,
                "claim_support_edges": claim_support_edges,
                "conflict_sets": conflict_sets,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    review_queue_path.write_text(
        ClaimReviewQueue(job_id=job_id, items=[]).model_dump_json(indent=2),
        encoding="utf-8",
    )
    return {"claim_graph_path": claim_graph_path, "review_queue_path": review_queue_path}


def _copy_task_artifacts(final_job, task_output_root: Path) -> dict[str, Path]:
    report_path = Path(final_job.report_path)
    bundle_dir = Path(final_job.report_bundle_path).parent
    audit_dir = Path(final_job.audit_graph_path).parent

    stable_report_path = task_output_root / "report.md"
    stable_bundle_dir = task_output_root / "bundle"
    stable_audit_dir = task_output_root / "audit"

    stable_report_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, stable_report_path)
    shutil.copytree(bundle_dir, stable_bundle_dir, dirs_exist_ok=True)
    if audit_dir.exists():
        shutil.copytree(audit_dir, stable_audit_dir, dirs_exist_ok=True)

    return {
        "report_path": stable_report_path,
        "bundle_path": stable_bundle_dir / "report_bundle.json",
        "manifest_path": stable_bundle_dir / "manifest.json",
        "trace_path": stable_bundle_dir / "trace.jsonl",
        "claim_graph_path": stable_audit_dir / "claim_graph.json",
        "review_queue_path": stable_audit_dir / "review_queue.json",
    }


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _normalize_task_artifacts(task: EvalTaskSpec, stable_paths: dict[str, Path]) -> None:
    bundle_path = stable_paths["bundle_path"]
    manifest_path = stable_paths["manifest_path"]
    trace_path = stable_paths["trace_path"]
    claim_graph_path = stable_paths["claim_graph_path"]
    review_queue_path = stable_paths["review_queue_path"]
    sources_path = bundle_path.parent / "sources.json"

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["job"]["job_id"] = task.task_id
    bundle["job"]["created_at"] = FROZEN_ARTIFACT_TIMESTAMP
    for snapshot in bundle.get("snapshots") or []:
        snapshot["fetched_at"] = FROZEN_ARTIFACT_TIMESTAMP
    normalized_events = []
    checkpoint_counter = 0
    for index, event in enumerate(bundle.get("audit_events") or [], start=1):
        updated = dict(event)
        payload = dict(updated.get("payload") or {})
        if "checkpoint_id" in payload:
            checkpoint_counter += 1
            payload["checkpoint_id"] = f"{task.task_id}-checkpoint-{checkpoint_counter:04d}"
        if updated.get("event_type") == "bundle.emitted":
            payload["report_path"] = _display_path(stable_paths["report_path"])
            payload["report_bundle_path"] = _display_path(stable_paths["bundle_path"])
            payload["trace_path"] = _display_path(stable_paths["trace_path"])
        updated["payload"] = payload
        updated["event_id"] = f"{task.task_id}-event-{index:04d}"
        updated["job_id"] = task.task_id
        updated["timestamp"] = FROZEN_ARTIFACT_TIMESTAMP
        normalized_events.append(updated)
    bundle["audit_events"] = normalized_events
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if sources_path.exists():
        sources_payload = {
            "citations": bundle.get("citations") or [],
            "sources": bundle.get("sources") or [],
            "snapshots": bundle.get("snapshots") or [],
        }
        sources_path.write_text(json.dumps(sources_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generated_at"] = FROZEN_ARTIFACT_TIMESTAMP
    manifest["job"]["job_id"] = task.task_id
    manifest["job"]["created_at"] = FROZEN_ARTIFACT_TIMESTAMP
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    trace_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in normalized_events) + "\n",
        encoding="utf-8",
    )

    if claim_graph_path.exists():
        claim_graph = json.loads(claim_graph_path.read_text(encoding="utf-8"))
        claim_graph["job_id"] = task.task_id
        claim_graph_path.write_text(json.dumps(claim_graph, ensure_ascii=False, indent=2), encoding="utf-8")
    if review_queue_path.exists():
        review_queue = json.loads(review_queue_path.read_text(encoding="utf-8"))
        review_queue["job_id"] = task.task_id
        review_queue["created_at"] = FROZEN_ARTIFACT_TIMESTAMP
        review_queue_path.write_text(json.dumps(review_queue, ensure_ascii=False, indent=2), encoding="utf-8")


def _compute_research_task_metrics(
    task: EvalTaskSpec,
    bundle: dict[str, Any],
    sources: list[SourceRecord],
    *,
    file_input_count: int,
) -> dict[str, Any]:
    claims = list(bundle.get("claims") or [])
    edges = list(bundle.get("claim_support_edges") or [])
    citations = list(bundle.get("citations") or [])
    bundle_sources = list(bundle.get("sources") or [])
    snapshots = {str(item.get("snapshot_id") or "") for item in bundle.get("snapshots") or []}
    high_claims = [claim for claim in claims if str(claim.get("criticality") or "") == "high"]
    supported_high = []
    blocking_high = []
    for claim in high_claims:
        claim_edges = [
            edge
            for edge in edges
            if str(edge.get("claim_id") or "") == str(claim.get("claim_id") or "")
            and str(edge.get("relation") or "") in {"supports", "partially_supports"}
            and str(edge.get("grounding_status") or "") == "grounded"
        ]
        if str(claim.get("status") or "") in SUPPORTED_CLAIM_STATUSES and claim_edges:
            supported_high.append(claim)
        if str(claim.get("status") or "") in BLOCKING_CLAIM_STATUSES or not claim_edges:
            blocking_high.append(claim)

    provenance_points = 0
    provenance_total = 0
    for source in bundle_sources:
        provenance_total += 1
        if str(source.get("snapshot_ref") or "") in snapshots:
            provenance_points += 1
    for citation in citations:
        provenance_total += 1
        if str(citation.get("snapshot_id") or "") in snapshots and str(citation.get("source_id") or "") in {
            str(source.get("source_id") or "") for source in bundle_sources
        }:
            provenance_points += 1
    provenance_completeness = round(provenance_points / provenance_total, 3) if provenance_total else 1.0

    policy = load_source_policy(task.source_profile)
    policy_passes = 0
    for source in sources:
        if source.auth_scope == "private":
            allowed = "private" in policy.auth_scopes and "files" in policy.connectors
        else:
            decision = policy.validate_fetch_uri(source.url or source.canonical_uri)
            allowed = decision.allowed and source.auth_scope in policy.auth_scopes
        if allowed:
            policy_passes += 1
    policy_compliance_rate = round(policy_passes / len(sources), 3) if sources else 1.0

    answered_questions = set(task.answered_questions)
    required_questions = list(task.required_questions)
    rubric_coverage = round(len(answered_questions.intersection(required_questions)) / len(required_questions), 3) if required_questions else 1.0
    conflict_expected = bool(task.conflict_sets)
    conflict_detection_recall = 1.0 if not conflict_expected else (1.0 if bundle.get("conflict_sets") else 0.0)
    file_sources = [source for source in sources if source.source_type == "files"]
    file_input_success_rate = round(len(file_sources) / file_input_count, 3) if file_input_count else 1.0
    return {
        "completion_rate": 1.0 if bundle.get("job", {}).get("status") == "completed" else 0.0,
        "bundle_emission_rate": 1.0,
        "audit_pass_rate": 1.0 if bundle.get("audit_summary", {}).get("gate_status") == "passed" else 0.0,
        "critical_claim_support_precision": round(len(supported_high) / len(high_claims), 3) if high_claims else 1.0,
        "citation_error_rate": round(len(blocking_high) / len(high_claims), 3) if high_claims else 0.0,
        "provenance_completeness": provenance_completeness,
        "rubric_coverage": rubric_coverage,
        "policy_compliance_rate": policy_compliance_rate,
        "file_input_success_rate": file_input_success_rate,
        "conflict_detection_recall": conflict_detection_recall,
    }


def _first_claim_text(report_markdown: str, topic: str) -> str:
    for raw_line in report_markdown.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return topic
