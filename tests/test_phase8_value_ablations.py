"""Phase 08 ablation and performance-pack regressions."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_value_ablation_pack_writes_required_outputs_and_statuses(tmp_path: Path):
    """Phase 8 should emit the required summary pack with honest ablation statuses."""
    from scripts import run_value_ablation_pack

    output_root = tmp_path / "followup_metrics"
    baseline_root = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke"
    followup_root = PROJECT_ROOT / "evals" / "reports" / "followup_metrics"

    run_value_ablation_pack.run_value_ablation_pack(
        baseline_root=baseline_root,
        followup_root=followup_root,
        output_root=output_root,
    )

    csv_path = output_root / "ablation_summary.csv"
    markdown_path = output_root / "ablation_summary.md"
    latency_path = output_root / "latency_cost_summary.json"
    provider_path = output_root / "provider_routing_comparison.json"

    assert csv_path.exists()
    assert markdown_path.exists()
    assert latency_path.exists()
    assert provider_path.exists()

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    statuses = {row["ablation_id"]: row["status"] for row in rows}

    assert statuses["audit_on_vs_off"] == "passed"
    assert statuses["strict_source_policy_vs_relaxed"] == "passed"
    assert statuses["evidence_first_vs_baseline_synthesis"] == "passed"
    assert statuses["rerank_on_vs_off"] == "passed"
    assert statuses["provider_auto_vs_manual"] == "passed"
    assert statuses["new_runtime_vs_legacy"] == "not_comparable"

    audit_row = next(row for row in rows if row["ablation_id"] == "audit_on_vs_off")
    audit_deltas = json.loads(audit_row["deltas_json"])
    assert audit_deltas["critical_claim_support_precision"] > 0
    assert audit_deltas["unsupported_claim_leakage_rate"] > 0


def test_provider_routing_comparison_records_auto_and_manual_routes(tmp_path: Path):
    """Provider routing comparison should preserve route reasons even without live latency/cost."""
    from scripts import run_value_ablation_pack

    output_root = tmp_path / "followup_metrics"
    baseline_root = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke"
    followup_root = PROJECT_ROOT / "evals" / "reports" / "followup_metrics"

    run_value_ablation_pack.run_value_ablation_pack(
        baseline_root=baseline_root,
        followup_root=followup_root,
        output_root=output_root,
    )

    comparison = _load_json(output_root / "provider_routing_comparison.json")
    judge = next(item for item in comparison["task_roles"] if item["task_role"] == "judge")

    assert comparison["status"] == "route_plan_only"
    assert comparison["latency_cost"]["reason"] == "no_live_provider_backed_routing_eval"
    assert judge["auto"]["selected_profile"]
    assert judge["auto"]["routing_mode"] == "auto"
    assert judge["auto"]["reason"].startswith("auto:")
    assert "openai" in judge["manual"]
    assert "anthropic" in judge["manual"]
    assert judge["manual"]["openai"]["routing_mode"] == "manual"
    assert "profile" not in judge["manual"]["openai"]
    assert "api_key" not in json.dumps(comparison)


def test_latency_cost_summary_reuses_phase7_measured_metrics(tmp_path: Path):
    """Latency/cost summary should be imported from the committed Phase 7 follow-up metrics."""
    from scripts import run_value_ablation_pack

    output_root = tmp_path / "followup_metrics"
    baseline_root = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke"
    followup_root = PROJECT_ROOT / "evals" / "reports" / "followup_metrics"

    run_value_ablation_pack.run_value_ablation_pack(
        baseline_root=baseline_root,
        followup_root=followup_root,
        output_root=output_root,
    )

    summary = _load_json(output_root / "latency_cost_summary.json")

    assert summary["ttff_seconds_p50"] == 0.299367
    assert summary["ttfr_seconds_p50"] == 1.344091
    assert summary["estimated_api_cost_per_completed_job"] is None
    assert summary["cost_reason"] == "provider_free_fixture_run"
    assert "clarifying" in summary["stage_runtime_seconds"]
