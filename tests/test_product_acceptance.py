"""Acceptance thresholds for the first trusted scientific-research corpus."""

from __future__ import annotations

from deep_research_agent.evals.product_acceptance import (
    ProductAcceptanceMetrics,
    evaluate_product_acceptance,
)


def _passing_metrics() -> ProductAcceptanceMetrics:
    return ProductAcceptanceMetrics(
        discovery_coverage=0.90,
        same_work_merge_precision=0.95,
        licensed_full_text_rate=1.0,
        critical_claim_traceability_rate=1.0,
        frozen_regeneration_rate=1.0,
        source_outage_warning_rate=1.0,
    )


def test_product_acceptance_uses_documented_thresholds() -> None:
    evaluation = evaluate_product_acceptance(_passing_metrics())

    assert evaluation.passed is True
    assert evaluation.thresholds["discovery_coverage"].minimum == 0.90
    assert evaluation.thresholds["same_work_merge_precision"].minimum == 0.95
    for metric_name in (
        "licensed_full_text_rate",
        "critical_claim_traceability_rate",
        "frozen_regeneration_rate",
        "source_outage_warning_rate",
    ):
        assert evaluation.thresholds[metric_name].minimum == 1.0
        assert evaluation.thresholds[metric_name].passed is True


def test_product_acceptance_reports_every_failed_gate() -> None:
    metrics = _passing_metrics().model_copy(
        update={
            "discovery_coverage": 0.89,
            "critical_claim_traceability_rate": 0.99,
            "source_outage_warning_rate": 0.5,
        }
    )

    evaluation = evaluate_product_acceptance(metrics)

    assert evaluation.passed is False
    assert evaluation.failed_metrics == (
        "critical_claim_traceability_rate",
        "discovery_coverage",
        "source_outage_warning_rate",
    )
    assert evaluation.thresholds["discovery_coverage"].reason == "0.89 < minimum 0.9"
