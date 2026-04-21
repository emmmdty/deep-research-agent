"""Phase 07 value-metrics aggregation and runtime-measurement regressions."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_value_metrics_emits_expected_pack_for_committed_smoke_root(tmp_path: Path):
    """Committed Phase 5 smoke artifacts should render a machine-readable value pack."""
    from scripts import run_value_metrics

    source_root = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke"
    output_root = tmp_path / "followup_metrics"

    pack = run_value_metrics.run_value_metrics_pack(
        source_roots=[source_root],
        output_root=output_root,
    )

    headline_path = output_root / "headline_metrics.json"
    dashboard_path = output_root / "value_dashboard.json"
    timing_path = output_root / "stage_timing_breakdown.json"

    assert headline_path.exists()
    assert dashboard_path.exists()
    assert timing_path.exists()

    headline = _load_json(headline_path)
    dashboard = _load_json(dashboard_path)
    timing = _load_json(timing_path)

    assert pack["artifacts"]["headline_metrics"] == str(headline_path)
    assert headline["metrics"]["completion_rate"]["value"] == 1.0
    assert headline["metrics"]["bundle_emission_rate"]["value"] == 1.0
    assert headline["metrics"]["resume_success_rate"]["value"] == 1.0
    assert headline["metrics"]["trusted_only_success_rate"]["value"] == 1.0
    assert headline["metrics"]["estimated_api_cost_per_completed_job"]["value"] is None
    assert headline["metrics"]["estimated_api_cost_per_completed_job"]["reason"] == "provider_free_fixture_run"
    assert headline["metrics"]["ttff_seconds_p50"]["value"] is None
    assert headline["metrics"]["ttff_seconds_p50"]["reason"] == "frozen_artifact_timestamps"
    assert dashboard["delivery"]["completion_rate"] == 1.0
    assert dashboard["reliability"]["resume_success_rate"] == 1.0
    assert timing["jobs"] == []
    assert timing["timing_status"] == "unavailable"


def test_eval_runner_can_emit_runtime_measurement_sidecar_for_fresh_suite(tmp_path: Path):
    """Fresh reruns should be able to save pre-normalization runtime timing metadata."""
    from deep_research_agent.evals.runner import run_eval_suite

    suite_root = tmp_path / "company12_fresh"
    result = run_eval_suite(
        suite_name="company12",
        output_root=suite_root,
        capture_runtime_metrics=True,
    )

    task_root = suite_root / result["tasks"][0]["task_id"]
    runtime_metrics_path = task_root / "runtime_metrics.json"

    assert runtime_metrics_path.exists()

    runtime_metrics = _load_json(runtime_metrics_path)

    assert runtime_metrics["job_id"] == "company-openai-surface"
    assert runtime_metrics["ttff_seconds"] is not None
    assert runtime_metrics["ttfr_seconds"] is not None
    assert runtime_metrics["stage_runtime_seconds"]["clarifying"] is not None
    assert runtime_metrics["prompt_tokens"] == 0
    assert runtime_metrics["completion_tokens"] == 0
    assert runtime_metrics["estimated_api_cost_usd"] is None
    assert runtime_metrics["cost_reason"] == "provider_free_fixture_run"


def test_run_value_metrics_uses_runtime_measurements_when_fresh_suite_is_present(tmp_path: Path):
    """Measured fresh suites should upgrade latency metrics from frozen-artifact nulls."""
    from deep_research_agent.evals.runner import run_eval_suite
    from scripts import run_value_metrics

    committed_root = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke"
    fresh_root = tmp_path / "company12_fresh"
    output_root = tmp_path / "followup_metrics"

    run_eval_suite(
        suite_name="company12",
        output_root=fresh_root,
        capture_runtime_metrics=True,
    )
    run_value_metrics.run_value_metrics_pack(
        source_roots=[committed_root, fresh_root],
        output_root=output_root,
    )

    headline = _load_json(output_root / "headline_metrics.json")
    timing = _load_json(output_root / "stage_timing_breakdown.json")

    assert headline["metrics"]["ttff_seconds_p50"]["value"] is not None
    assert headline["metrics"]["ttff_seconds_p50"]["sample_size"] >= 1
    assert headline["metrics"]["ttfr_seconds_p50"]["value"] is not None
    assert timing["timing_status"] == "measured"
    assert timing["jobs"][0]["job_id"] == "company-openai-surface"
    assert timing["stage_summary"]["clarifying"]["count"] >= 1
