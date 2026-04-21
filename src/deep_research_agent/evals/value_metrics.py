"""Canonical follow-up value-metrics aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FROZEN_TIMING_REASON = "frozen_artifact_timestamps"
PROVIDER_FREE_COST_REASON = "provider_free_fixture_run"


def build_value_metrics_pack(*, source_roots: list[str | Path], output_root: str | Path) -> dict[str, Any]:
    """Aggregate follow-up metrics from one or more release or suite roots."""

    resolved_roots = [Path(root).resolve() for root in source_roots]
    resolved_output_root = Path(output_root).resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    suites = _load_suite_inputs(resolved_roots)
    timing_breakdown = _build_stage_timing_breakdown(suites)
    headline = _build_headline_metrics(suites, timing_breakdown=timing_breakdown)
    dashboard = _build_value_dashboard(headline, suites=suites, timing_breakdown=timing_breakdown)

    headline_path = resolved_output_root / "headline_metrics.json"
    dashboard_path = resolved_output_root / "value_dashboard.json"
    timing_path = resolved_output_root / "stage_timing_breakdown.json"

    _write_json(headline_path, headline)
    _write_json(dashboard_path, dashboard)
    _write_json(timing_path, timing_breakdown)

    return {
        "source_roots": [str(root) for root in resolved_roots],
        "artifacts": {
            "headline_metrics": str(headline_path),
            "value_dashboard": str(dashboard_path),
            "stage_timing_breakdown": str(timing_path),
        },
    }


def _build_headline_metrics(
    suites: dict[str, dict[str, Any]],
    *,
    timing_breakdown: dict[str, Any],
) -> dict[str, Any]:
    task_bundles = _research_task_bundles(suites)
    runtime_measurements = _runtime_measurements(task_bundles)
    provider_free_only = all(_bundle_is_provider_free(item["bundle"]) for item in task_bundles) if task_bundles else False

    metrics = {
        "completion_rate": _weighted_suite_metric(suites, "completion_rate"),
        "bundle_emission_rate": _weighted_suite_metric(suites, "bundle_emission_rate"),
        "rubric_coverage": _weighted_suite_metric(suites, "rubric_coverage"),
        "critical_claim_support_precision": _weighted_suite_metric(suites, "critical_claim_support_precision"),
        "citation_error_rate": _weighted_suite_metric(suites, "citation_error_rate"),
        "provenance_completeness": _weighted_suite_metric(suites, "provenance_completeness"),
        "audit_pass_rate": _weighted_suite_metric(suites, "audit_pass_rate"),
        "policy_compliance_rate": _weighted_suite_metric(suites, "policy_compliance_rate"),
        "trusted_only_success_rate": _trusted_only_success_rate(task_bundles),
        "cancel_success_rate": _weighted_suite_metric(suites, "cancel_success_rate"),
        "retry_success_rate": _weighted_suite_metric(suites, "retry_success_rate"),
        "resume_success_rate": _weighted_suite_metric(suites, "resume_success_rate"),
        "refine_success_rate": _weighted_suite_metric(suites, "refine_success_rate"),
        "stale_recovery_success_rate": _weighted_suite_metric(suites, "stale_recovery_success_rate"),
        "idle_skip_rate": _weighted_suite_metric(suites, "idle_skip_rate"),
        "file_input_success_rate": _weighted_suite_metric(suites, "file_input_success_rate"),
        "conflict_detection_recall": _weighted_suite_metric(suites, "conflict_detection_recall"),
        "source_count_per_job": _mean_bundle_count(task_bundles, "sources"),
        "evidence_count_per_job": _mean_bundle_count(task_bundles, "evidence_fragments"),
        "claim_count_per_job": _mean_bundle_count(task_bundles, "claims"),
        "prompt_tokens_per_completed_job": _token_metric(runtime_measurements, "prompt_tokens", provider_free_only=provider_free_only),
        "completion_tokens_per_completed_job": _token_metric(
            runtime_measurements,
            "completion_tokens",
            provider_free_only=provider_free_only,
        ),
        "estimated_api_cost_per_completed_job": _cost_metric(
            runtime_measurements,
            provider_free_only=provider_free_only,
            fallback_jobs=len(task_bundles),
        ),
        "ttff_seconds_p50": _latency_metric(runtime_measurements, "ttff_seconds", percentile="p50"),
        "ttff_seconds_p95": _latency_metric(runtime_measurements, "ttff_seconds", percentile="p95"),
        "ttfr_seconds_p50": _latency_metric(runtime_measurements, "ttfr_seconds", percentile="p50"),
        "ttfr_seconds_p95": _latency_metric(runtime_measurements, "ttfr_seconds", percentile="p95"),
        "stage_runtime_seconds": {
            "value": timing_breakdown["stage_summary"],
            "sample_size": len(timing_breakdown["jobs"]),
            "reason": None if timing_breakdown["jobs"] else FROZEN_TIMING_REASON,
        },
    }
    return {
        "generated_at": _generated_at(),
        "source_roots": [suite["source_root"] for suite in suites.values()],
        "metrics": metrics,
    }


def _build_value_dashboard(
    headline: dict[str, Any],
    *,
    suites: dict[str, dict[str, Any]],
    timing_breakdown: dict[str, Any],
) -> dict[str, Any]:
    metric_values = {name: payload["value"] for name, payload in headline["metrics"].items()}
    return {
        "generated_at": headline["generated_at"],
        "source_roots": headline["source_roots"],
        "delivery": {
            "completion_rate": metric_values["completion_rate"],
            "bundle_emission_rate": metric_values["bundle_emission_rate"],
            "rubric_coverage": metric_values["rubric_coverage"],
        },
        "trustworthiness": {
            "critical_claim_support_precision": metric_values["critical_claim_support_precision"],
            "citation_error_rate": metric_values["citation_error_rate"],
            "provenance_completeness": metric_values["provenance_completeness"],
            "audit_pass_rate": metric_values["audit_pass_rate"],
        },
        "governance": {
            "policy_compliance_rate": metric_values["policy_compliance_rate"],
            "trusted_only_success_rate": metric_values["trusted_only_success_rate"],
        },
        "reliability": {
            "cancel_success_rate": metric_values["cancel_success_rate"],
            "retry_success_rate": metric_values["retry_success_rate"],
            "resume_success_rate": metric_values["resume_success_rate"],
            "refine_success_rate": metric_values["refine_success_rate"],
            "stale_recovery_success_rate": metric_values["stale_recovery_success_rate"],
            "idle_skip_rate": metric_values["idle_skip_rate"],
        },
        "cross_source": {
            "file_input_success_rate": metric_values["file_input_success_rate"],
            "conflict_detection_recall": metric_values["conflict_detection_recall"],
            "source_count_per_job": metric_values["source_count_per_job"],
            "evidence_count_per_job": metric_values["evidence_count_per_job"],
            "claim_count_per_job": metric_values["claim_count_per_job"],
        },
        "efficiency": {
            "ttff_seconds_p50": metric_values["ttff_seconds_p50"],
            "ttff_seconds_p95": metric_values["ttff_seconds_p95"],
            "ttfr_seconds_p50": metric_values["ttfr_seconds_p50"],
            "ttfr_seconds_p95": metric_values["ttfr_seconds_p95"],
            "prompt_tokens_per_completed_job": metric_values["prompt_tokens_per_completed_job"],
            "completion_tokens_per_completed_job": metric_values["completion_tokens_per_completed_job"],
            "estimated_api_cost_per_completed_job": metric_values["estimated_api_cost_per_completed_job"],
        },
        "timing_status": timing_breakdown["timing_status"],
        "suite_statuses": {
            suite_name: suite["summary"]["status"]
            for suite_name, suite in sorted(suites.items())
        },
    }


def _build_stage_timing_breakdown(suites: dict[str, dict[str, Any]]) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    stage_values: dict[str, list[float]] = {}
    for suite_name, suite in suites.items():
        for task in suite["tasks"]:
            runtime_metrics = task.get("runtime_metrics")
            if not runtime_metrics:
                continue
            jobs.append(
                {
                    "suite_name": suite_name,
                    "task_id": task["task"].get("task_id"),
                    "job_id": runtime_metrics["job_id"],
                    "ttff_seconds": runtime_metrics.get("ttff_seconds"),
                    "ttfr_seconds": runtime_metrics.get("ttfr_seconds"),
                    "stage_runtime_seconds": runtime_metrics.get("stage_runtime_seconds", {}),
                }
            )
            for stage_name, value in (runtime_metrics.get("stage_runtime_seconds") or {}).items():
                stage_values.setdefault(stage_name, []).append(float(value))

    stage_summary = {
        stage_name: {
            "count": len(values),
            "p50_seconds": _percentile(values, "p50"),
            "p95_seconds": _percentile(values, "p95"),
            "avg_seconds": round(sum(values) / len(values), 6),
        }
        for stage_name, values in sorted(stage_values.items())
    }
    return {
        "generated_at": _generated_at(),
        "timing_status": "measured" if jobs else "unavailable",
        "jobs": jobs,
        "stage_summary": stage_summary,
    }


def _load_suite_inputs(source_roots: list[Path]) -> dict[str, dict[str, Any]]:
    suites: dict[str, dict[str, Any]] = {}
    for source_root in source_roots:
        for suite_root in _discover_suite_roots(source_root):
            summary = _load_json(suite_root / "summary.json")
            suite_name = str(summary["suite_name"])
            suites[suite_name] = {
                "source_root": str(source_root),
                "suite_root": str(suite_root),
                "summary": summary,
                "tasks": _load_task_inputs(summary, suite_root=suite_root),
            }
    return suites


def _discover_suite_roots(source_root: Path) -> list[Path]:
    if (source_root / "summary.json").exists():
        return [source_root]
    manifest_path = source_root / "release_manifest.json"
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        suite_order = manifest.get("suite_order") or []
        return [source_root / str(suite_name) for suite_name in suite_order]
    raise FileNotFoundError(f"unsupported source root: {source_root}")


def _load_task_inputs(summary: dict[str, Any], *, suite_root: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for task in summary.get("tasks") or []:
        bundle = None
        runtime_metrics = None
        bundle_path = task.get("bundle_path")
        if bundle_path:
            resolved_bundle_path = _resolve_artifact_path(str(bundle_path), suite_root=suite_root)
            bundle = _load_json(resolved_bundle_path)
            runtime_metrics_path = resolved_bundle_path.parents[1] / "runtime_metrics.json"
            if runtime_metrics_path.exists():
                runtime_metrics = _load_json(runtime_metrics_path)
        tasks.append(
            {
                "task": task,
                "bundle": bundle,
                "runtime_metrics": runtime_metrics,
            }
        )
    return tasks


def _resolve_artifact_path(path_str: str, *, suite_root: Path) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    project_candidate = (PROJECT_ROOT / path).resolve()
    if project_candidate.exists():
        return project_candidate
    return (suite_root / path).resolve()


def _weighted_suite_metric(suites: dict[str, dict[str, Any]], metric_name: str) -> dict[str, Any]:
    weighted_sum = 0.0
    total_weight = 0
    for suite in suites.values():
        metrics = dict(suite["summary"].get("metrics") or {})
        if metric_name not in metrics:
            continue
        weight = int(suite["summary"].get("task_count") or 0) or 1
        weighted_sum += float(metrics[metric_name]) * weight
        total_weight += weight
    if total_weight == 0:
        return {"value": None, "sample_size": 0, "reason": "metric_not_available"}
    return {
        "value": round(weighted_sum / total_weight, 3),
        "sample_size": total_weight,
        "reason": None,
    }


def _trusted_only_success_rate(task_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    trusted_only = [
        item
        for item in task_bundles
        if str(item["bundle"].get("job", {}).get("source_profile") or "") == "trusted_only"
    ]
    if not trusted_only:
        return {"value": None, "sample_size": 0, "reason": "trusted_only_tasks_missing"}
    passed = sum(
        1
        for item in trusted_only
        if str(item["bundle"].get("job", {}).get("status") or "") == "completed"
    )
    return {
        "value": round(passed / len(trusted_only), 3),
        "sample_size": len(trusted_only),
        "reason": None,
    }


def _mean_bundle_count(task_bundles: list[dict[str, Any]], field_name: str) -> dict[str, Any]:
    if not task_bundles:
        return {"value": None, "sample_size": 0, "reason": "bundle_metrics_missing"}
    values = [len(item["bundle"].get(field_name) or []) for item in task_bundles]
    return {
        "value": round(sum(values) / len(values), 3),
        "sample_size": len(values),
        "reason": None,
    }


def _token_metric(runtime_measurements: list[dict[str, Any]], field_name: str, *, provider_free_only: bool) -> dict[str, Any]:
    if runtime_measurements:
        values = [int(item.get(field_name) or 0) for item in runtime_measurements]
        return {
            "value": round(sum(values) / len(values), 3),
            "sample_size": len(values),
            "reason": None,
        }
    if provider_free_only:
        return {"value": 0, "sample_size": 0, "reason": None}
    return {"value": None, "sample_size": 0, "reason": "token_usage_not_available"}


def _cost_metric(runtime_measurements: list[dict[str, Any]], *, provider_free_only: bool, fallback_jobs: int) -> dict[str, Any]:
    values = [item.get("estimated_api_cost_usd") for item in runtime_measurements if item.get("estimated_api_cost_usd") is not None]
    if values:
        numeric = [float(value) for value in values]
        return {
            "value": round(sum(numeric) / len(numeric), 6),
            "sample_size": len(numeric),
            "reason": None,
        }
    if provider_free_only:
        return {
            "value": None,
            "sample_size": fallback_jobs,
            "reason": PROVIDER_FREE_COST_REASON,
        }
    return {
        "value": None,
        "sample_size": len(runtime_measurements),
        "reason": "cost_not_recorded",
    }


def _latency_metric(runtime_measurements: list[dict[str, Any]], field_name: str, *, percentile: str) -> dict[str, Any]:
    values = [float(item[field_name]) for item in runtime_measurements if item.get(field_name) is not None]
    if not values:
        return {"value": None, "sample_size": 0, "reason": FROZEN_TIMING_REASON}
    return {
        "value": _percentile(values, percentile),
        "sample_size": len(values),
        "reason": None,
    }


def _percentile(values: list[float], percentile: str) -> float:
    ordered = sorted(values)
    if percentile == "p50":
        return round(float(median(ordered)), 6)
    if percentile == "p95":
        index = max(0, int(len(ordered) * 0.95 + 0.999999) - 1)
        index = min(index, len(ordered) - 1)
        return round(float(ordered[index]), 6)
    raise ValueError(f"unsupported percentile: {percentile}")


def _research_task_bundles(suites: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    task_bundles = []
    for suite_name, suite in suites.items():
        for task in suite["tasks"]:
            if task.get("bundle") is None:
                continue
            task_bundles.append({"suite_name": suite_name, **task})
    return task_bundles


def _runtime_measurements(task_bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item["runtime_metrics"] for item in task_bundles if item.get("runtime_metrics")]


def _bundle_is_provider_free(bundle: dict[str, Any]) -> bool:
    budget = dict(bundle.get("job", {}).get("budget") or {})
    return int(budget.get("llm_calls") or 0) == 0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _generated_at() -> str:
    # Keep follow-up pack deterministic within a single command invocation.
    return "2026-04-21T00:00:00+00:00"
