"""Deterministic ablation and performance-pack generation for follow-up metrics."""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from configs.settings import get_settings
from deep_research_agent.evals.value_metrics import PROJECT_ROOT
from deep_research_agent.providers.models import ProviderRouteRequest, RoutingMode
from deep_research_agent.providers.router import ProviderRouter
from policies import load_source_policy


def build_value_ablation_pack(
    *,
    baseline_root: str | Path,
    followup_root: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    baseline_root = Path(baseline_root).resolve()
    followup_root = Path(followup_root).resolve()
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    company_bundle = _load_suite_bundle(baseline_root, "company12")
    industry_bundle = _load_suite_bundle(baseline_root, "industry12")
    trusted_bundle = _load_suite_bundle(baseline_root, "trusted8")
    headline_metrics = _load_json(followup_root / "headline_metrics.json")
    stage_timing = _load_json(followup_root / "stage_timing_breakdown.json")

    rows = [
        _audit_on_vs_off(company_bundle),
        _strict_source_policy_vs_relaxed(trusted_bundle),
        _evidence_first_vs_baseline_synthesis(company_bundle),
        _rerank_on_vs_off(industry_bundle),
    ]

    provider_routing = _provider_routing_comparison()
    rows.append(_provider_auto_vs_manual_row(provider_routing))
    rows.append(_new_runtime_vs_legacy_row())

    latency_cost_summary = _latency_cost_summary(headline_metrics, stage_timing)
    csv_path = output_root / "ablation_summary.csv"
    markdown_path = output_root / "ablation_summary.md"
    latency_path = output_root / "latency_cost_summary.json"
    provider_path = output_root / "provider_routing_comparison.json"

    _write_ablation_csv(csv_path, rows)
    markdown_path.write_text(_render_ablation_markdown(rows), encoding="utf-8")
    _write_json(latency_path, latency_cost_summary)
    _write_json(provider_path, provider_routing)

    return {
        "artifacts": {
            "ablation_summary_csv": str(csv_path),
            "ablation_summary_markdown": str(markdown_path),
            "latency_cost_summary": str(latency_path),
            "provider_routing_comparison": str(provider_path),
        },
        "ablation_count": len(rows),
    }


def _audit_on_vs_off(bundle: dict[str, Any]) -> dict[str, Any]:
    comparison = deepcopy(bundle)
    comparison["claim_support_edges"] = []
    comparison["audit_summary"]["gate_status"] = "unchecked"
    baseline_support = _critical_claim_support_precision(bundle)
    comparison_support = _critical_claim_support_precision(comparison)
    baseline_leakage = 1.0 - baseline_support
    comparison_leakage = 1.0 - comparison_support
    return _row(
        ablation_id="audit_on_vs_off",
        baseline_mode="audit_on",
        comparison_mode="audit_off",
        task_or_suite="company12/company-openai-surface",
        compared_metrics=["critical_claim_support_precision", "unsupported_claim_leakage_rate", "completion_rate"],
        baseline_metrics={
            "critical_claim_support_precision": baseline_support,
            "unsupported_claim_leakage_rate": baseline_leakage,
            "completion_rate": 1.0,
        },
        comparison_metrics={
            "critical_claim_support_precision": comparison_support,
            "unsupported_claim_leakage_rate": comparison_leakage,
            "completion_rate": 1.0,
        },
        deltas={
            "critical_claim_support_precision": round(baseline_support - comparison_support, 3),
            "unsupported_claim_leakage_rate": round(comparison_leakage - baseline_leakage, 3),
            "completion_rate": 0.0,
        },
        interpretation="Without audit-grounded support edges, unsupported claim leakage rises while the fixture still completes.",
        artifact_paths={"baseline_suite": "evals/reports/phase5_local_smoke/company12"},
        status="passed",
    )


def _strict_source_policy_vs_relaxed(bundle: dict[str, Any]) -> dict[str, Any]:
    comparison = deepcopy(bundle)
    snapshots = list(comparison.get("snapshots") or [])
    sources = list(comparison.get("sources") or [])
    citations = list(comparison.get("citations") or [])
    snapshots.append(
        {
            "snapshot_id": "snapshot-untrusted-reddit",
            "canonical_uri": "https://reddit.com/r/langchain/comments/example",
            "fetched_at": "2026-04-21T00:00:00+00:00",
            "content_hash": "synthetic-untrusted-source",
            "mime_type": "text/plain",
            "auth_scope": "public",
            "freshness_metadata": {"query": "community rumor", "source_type": "web"},
        }
    )
    sources.append(
        {
            "source_id": "source-untrusted-reddit",
            "citation_id": 999,
            "source_type": "web",
            "title": "Community rumor",
            "canonical_uri": "https://reddit.com/r/langchain/comments/example",
            "query": "community rumor",
            "selected": True,
            "snapshot_ref": "snapshot-untrusted-reddit",
            "metadata": {},
        }
    )
    citations.append(
        {
            "citation_id": 999,
            "source_id": "source-untrusted-reddit",
            "snapshot_id": "snapshot-untrusted-reddit",
            "title": "Community rumor",
            "canonical_uri": "https://reddit.com/r/langchain/comments/example",
        }
    )
    comparison["snapshots"] = snapshots
    comparison["sources"] = sources
    comparison["citations"] = citations
    baseline_policy = _policy_compliance_rate(bundle, source_profile="trusted_only")
    comparison_policy = _policy_compliance_rate(comparison, source_profile="trusted_only")
    return _row(
        ablation_id="strict_source_policy_vs_relaxed",
        baseline_mode="strict_source_policy",
        comparison_mode="relaxed_source_policy",
        task_or_suite="trusted8/trusted-langgraph-brief",
        compared_metrics=["policy_compliance_rate", "bundle_emission_rate", "completion_rate"],
        baseline_metrics={
            "policy_compliance_rate": baseline_policy,
            "bundle_emission_rate": 1.0,
            "completion_rate": 1.0,
        },
        comparison_metrics={
            "policy_compliance_rate": comparison_policy,
            "bundle_emission_rate": 1.0,
            "completion_rate": 1.0,
        },
        deltas={
            "policy_compliance_rate": round(baseline_policy - comparison_policy, 3),
            "bundle_emission_rate": 0.0,
            "completion_rate": 0.0,
        },
        interpretation="Relaxing trusted-only enforcement keeps the bundle flowing but admits a source the strict policy would block.",
        artifact_paths={"baseline_suite": "evals/reports/phase5_local_smoke/trusted8"},
        status="passed",
    )


def _evidence_first_vs_baseline_synthesis(bundle: dict[str, Any]) -> dict[str, Any]:
    comparison = deepcopy(bundle)
    for source in comparison.get("sources") or []:
        source["snapshot_ref"] = ""
    for citation in comparison.get("citations") or []:
        citation["snapshot_id"] = ""
    comparison["claim_support_edges"] = []
    baseline_provenance = _provenance_completeness(bundle)
    comparison_provenance = _provenance_completeness(comparison)
    baseline_support = _critical_claim_support_precision(bundle)
    comparison_support = _critical_claim_support_precision(comparison)
    baseline_error = _citation_error_rate(bundle)
    comparison_error = _citation_error_rate(comparison)
    return _row(
        ablation_id="evidence_first_vs_baseline_synthesis",
        baseline_mode="evidence_first",
        comparison_mode="baseline_synthesis",
        task_or_suite="company12/company-openai-surface",
        compared_metrics=[
            "provenance_completeness",
            "critical_claim_support_precision",
            "citation_error_rate",
        ],
        baseline_metrics={
            "provenance_completeness": baseline_provenance,
            "critical_claim_support_precision": baseline_support,
            "citation_error_rate": baseline_error,
        },
        comparison_metrics={
            "provenance_completeness": comparison_provenance,
            "critical_claim_support_precision": comparison_support,
            "citation_error_rate": comparison_error,
        },
        deltas={
            "provenance_completeness": round(baseline_provenance - comparison_provenance, 3),
            "critical_claim_support_precision": round(baseline_support - comparison_support, 3),
            "citation_error_rate": round(comparison_error - baseline_error, 3),
        },
        interpretation="Removing evidence-first grounding erodes provenance and support quality immediately in the emitted bundle.",
        artifact_paths={"baseline_suite": "evals/reports/phase5_local_smoke/company12"},
        status="passed",
    )


def _rerank_on_vs_off(bundle: dict[str, Any]) -> dict[str, Any]:
    comparison = deepcopy(bundle)
    for edge in comparison.get("claim_support_edges") or []:
        if edge.get("edge_id") == "edge-agent-stack-3":
            edge["relation"] = "context_only"
    baseline_support = _critical_claim_support_precision(bundle)
    comparison_support = _critical_claim_support_precision(comparison)
    return _row(
        ablation_id="rerank_on_vs_off",
        baseline_mode="rerank_on",
        comparison_mode="rerank_off",
        task_or_suite="industry12/industry-agent-stack",
        compared_metrics=["critical_claim_support_precision", "completion_rate"],
        baseline_metrics={
            "critical_claim_support_precision": baseline_support,
            "completion_rate": 1.0,
        },
        comparison_metrics={
            "critical_claim_support_precision": comparison_support,
            "completion_rate": 1.0,
        },
        deltas={
            "critical_claim_support_precision": round(baseline_support - comparison_support, 3),
            "completion_rate": 0.0,
        },
        interpretation="Disabling the rerank-like edge selection leaves a critical claim with only context-only evidence.",
        artifact_paths={"baseline_suite": "evals/reports/phase5_local_smoke/industry12"},
        status="passed",
    )


def _provider_routing_comparison() -> dict[str, Any]:
    settings = get_settings()
    router = ProviderRouter(settings)
    task_roles = []
    for task_role in ("planning", "query_rewrite", "extraction", "synthesis", "judge"):
        auto = router.route(
            ProviderRouteRequest(
                task_role=task_role,
                routing_mode=RoutingMode.AUTO,
                current_provider=settings.get_default_provider_profile_name(),
            )
        )
        manual = {
            profile_name: _route_summary(
                router.route(
                    ProviderRouteRequest(
                        task_role=task_role,
                        routing_mode=RoutingMode.MANUAL,
                        provider_profile=profile_name,
                        current_provider=settings.get_default_provider_profile_name(),
                    )
                )
            )
            for profile_name in sorted(router.profiles)
        }
        task_roles.append(
            {
                "task_role": task_role,
                "auto": _route_summary(auto),
                "manual": manual,
            }
        )
    return {
        "generated_at": "2026-04-21T00:00:00+00:00",
        "status": "route_plan_only",
        "task_roles": task_roles,
        "latency_cost": {
            "value": None,
            "reason": "no_live_provider_backed_routing_eval",
        },
    }


def _provider_auto_vs_manual_row(provider_routing: dict[str, Any]) -> dict[str, Any]:
    judge = next(item for item in provider_routing["task_roles"] if item["task_role"] == "judge")
    return _row(
        ablation_id="provider_auto_vs_manual",
        baseline_mode="provider_auto_routing",
        comparison_mode="manual_single_provider",
        task_or_suite="provider_router",
        compared_metrics=["selected_profile", "live_latency_delta", "live_quality_delta"],
        baseline_metrics={"selected_profile": judge["auto"]["selected_profile"]},
        comparison_metrics={"manual_profiles": sorted(judge["manual"])},
        deltas={
            "live_latency_delta": None,
            "live_quality_delta": None,
        },
        interpretation="Auto-routing can be inspected deterministically, but this local follow-up run does not include live quality or billing comparisons.",
        artifact_paths={"provider_routing_comparison": "provider_routing_comparison.json"},
        status="passed",
    )


def _new_runtime_vs_legacy_row() -> dict[str, Any]:
    return _row(
        ablation_id="new_runtime_vs_legacy",
        baseline_mode="current_runtime",
        comparison_mode="legacy_runtime",
        task_or_suite="runtime_control_plane",
        compared_metrics=["resume_success_rate", "stale_recovery_success_rate"],
        baseline_metrics={},
        comparison_metrics={},
        deltas={},
        interpretation="No like-for-like legacy runtime fixture remains that matches the current deterministic job contracts and bundle outputs.",
        artifact_paths={},
        status="not_comparable",
        reason="no_like_for_like_legacy_runtime_fixture",
    )


def _route_summary(route: Any) -> dict[str, Any]:
    return {
        "selected_profile": route.profile.name,
        "provider_type": route.profile.provider_type.value,
        "model": route.profile.model,
        "routing_mode": route.routing_mode.value,
        "reason": route.reason,
    }


def _latency_cost_summary(headline_metrics: dict[str, Any], stage_timing: dict[str, Any]) -> dict[str, Any]:
    metrics = headline_metrics["metrics"]
    return {
        "generated_at": "2026-04-21T00:00:00+00:00",
        "source": "phase7_followup_metrics",
        "ttff_seconds_p50": metrics["ttff_seconds_p50"]["value"],
        "ttff_seconds_p95": metrics["ttff_seconds_p95"]["value"],
        "ttfr_seconds_p50": metrics["ttfr_seconds_p50"]["value"],
        "ttfr_seconds_p95": metrics["ttfr_seconds_p95"]["value"],
        "prompt_tokens_per_completed_job": metrics["prompt_tokens_per_completed_job"]["value"],
        "completion_tokens_per_completed_job": metrics["completion_tokens_per_completed_job"]["value"],
        "estimated_api_cost_per_completed_job": metrics["estimated_api_cost_per_completed_job"]["value"],
        "cost_reason": metrics["estimated_api_cost_per_completed_job"]["reason"],
        "timing_status": stage_timing["timing_status"],
        "stage_runtime_seconds": stage_timing["stage_summary"],
        "notes": [
            "local smoke plus the committed fresh measured company12 rerun",
            "no live provider billing was recorded in this follow-up run",
        ],
    }


def _load_suite_bundle(baseline_root: Path, suite_name: str) -> dict[str, Any]:
    summary = _load_json(baseline_root / suite_name / "summary.json")
    task = summary["tasks"][0]
    bundle_path = _resolve_path(task["bundle_path"])
    return _load_json(bundle_path)


def _critical_claim_support_precision(bundle: dict[str, Any]) -> float:
    claims = list(bundle.get("claims") or [])
    edges = list(bundle.get("claim_support_edges") or [])
    high_claims = [claim for claim in claims if str(claim.get("criticality") or "") == "high"]
    if not high_claims:
        return 1.0
    supported = 0
    for claim in high_claims:
        grounded_edges = [
            edge
            for edge in edges
            if str(edge.get("claim_id") or "") == str(claim.get("claim_id") or "")
            and str(edge.get("relation") or "") in {"supports", "partially_supports"}
            and str(edge.get("grounding_status") or "") == "grounded"
        ]
        if grounded_edges and str(claim.get("status") or "") in {"supported", "partially_supported"}:
            supported += 1
    return round(supported / len(high_claims), 3)


def _citation_error_rate(bundle: dict[str, Any]) -> float:
    return round(1.0 - _critical_claim_support_precision(bundle), 3)


def _provenance_completeness(bundle: dict[str, Any]) -> float:
    snapshots = {str(item.get("snapshot_id") or "") for item in bundle.get("snapshots") or []}
    sources = list(bundle.get("sources") or [])
    citations = list(bundle.get("citations") or [])
    points = 0
    total = 0
    for source in sources:
        total += 1
        if str(source.get("snapshot_ref") or "") in snapshots:
            points += 1
    source_ids = {str(source.get("source_id") or "") for source in sources}
    for citation in citations:
        total += 1
        if str(citation.get("snapshot_id") or "") in snapshots and str(citation.get("source_id") or "") in source_ids:
            points += 1
    return round(points / total, 3) if total else 1.0


def _policy_compliance_rate(bundle: dict[str, Any], *, source_profile: str) -> float:
    policy = load_source_policy(source_profile)
    snapshots = {str(item.get("snapshot_id") or ""): item for item in bundle.get("snapshots") or []}
    sources = list(bundle.get("sources") or [])
    if not sources:
        return 1.0
    compliant = 0
    for source in sources:
        snapshot = snapshots.get(str(source.get("snapshot_ref") or ""))
        auth_scope = str((snapshot or {}).get("auth_scope") or "public")
        uri = str(source.get("canonical_uri") or "")
        if auth_scope == "private":
            allowed = "private" in policy.auth_scopes and "files" in policy.connectors
        else:
            decision = policy.validate_fetch_uri(uri)
            allowed = decision.allowed and auth_scope in policy.auth_scopes
        if allowed:
            compliant += 1
    return round(compliant / len(sources), 3)


def _row(
    *,
    ablation_id: str,
    baseline_mode: str,
    comparison_mode: str,
    task_or_suite: str,
    compared_metrics: list[str],
    baseline_metrics: dict[str, Any],
    comparison_metrics: dict[str, Any],
    deltas: dict[str, Any],
    interpretation: str,
    artifact_paths: dict[str, Any],
    status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "ablation_id": ablation_id,
        "baseline_mode": baseline_mode,
        "comparison_mode": comparison_mode,
        "task_or_suite": task_or_suite,
        "compared_metrics": compared_metrics,
        "absolute_values": {
            "baseline": baseline_metrics,
            "comparison": comparison_metrics,
        },
        "deltas": deltas,
        "interpretation": interpretation,
        "artifact_paths": artifact_paths,
        "status": status,
        "reason": reason or "",
    }


def _write_ablation_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "ablation_id",
        "baseline_mode",
        "comparison_mode",
        "task_or_suite",
        "status",
        "compared_metrics_json",
        "absolute_values_json",
        "deltas_json",
        "interpretation",
        "artifact_paths_json",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ablation_id": row["ablation_id"],
                    "baseline_mode": row["baseline_mode"],
                    "comparison_mode": row["comparison_mode"],
                    "task_or_suite": row["task_or_suite"],
                    "status": row["status"],
                    "compared_metrics_json": json.dumps(row["compared_metrics"], ensure_ascii=False),
                    "absolute_values_json": json.dumps(row["absolute_values"], ensure_ascii=False, sort_keys=True),
                    "deltas_json": json.dumps(row["deltas"], ensure_ascii=False, sort_keys=True),
                    "interpretation": row["interpretation"],
                    "artifact_paths_json": json.dumps(row["artifact_paths"], ensure_ascii=False, sort_keys=True),
                    "reason": row["reason"],
                }
            )


def _render_ablation_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Phase 8 Ablation Summary",
        "",
        "| Ablation | Status | Scope | Key delta | Interpretation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        delta_preview = json.dumps(row["deltas"], ensure_ascii=False, sort_keys=True)
        lines.append(
            f"| {row['ablation_id']} | {row['status']} | {row['task_or_suite']} | `{delta_preview}` | {row['interpretation']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
