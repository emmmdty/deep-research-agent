"""Auditable acceptance thresholds for the first scholarly corpus product."""

from __future__ import annotations

import argparse

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProductAcceptanceMetrics(StrictModel):
    discovery_coverage: float = Field(ge=0, le=1)
    same_work_merge_precision: float = Field(ge=0, le=1)
    licensed_full_text_rate: float = Field(ge=0, le=1)
    critical_claim_traceability_rate: float = Field(ge=0, le=1)
    frozen_regeneration_rate: float = Field(ge=0, le=1)
    source_outage_warning_rate: float = Field(ge=0, le=1)


class AcceptanceThresholdResult(StrictModel):
    value: float
    minimum: float
    passed: bool
    reason: str = ""


class ProductAcceptanceEvaluation(StrictModel):
    passed: bool
    thresholds: dict[str, AcceptanceThresholdResult]
    failed_metrics: tuple[str, ...]


ACCEPTANCE_MINIMUMS: dict[str, float] = {
    "discovery_coverage": 0.90,
    "same_work_merge_precision": 0.95,
    "licensed_full_text_rate": 1.0,
    "critical_claim_traceability_rate": 1.0,
    "frozen_regeneration_rate": 1.0,
    "source_outage_warning_rate": 1.0,
}


def evaluate_product_acceptance(
    metrics: ProductAcceptanceMetrics,
) -> ProductAcceptanceEvaluation:
    """Evaluate all published corpus gates without averages hiding failures."""

    values = metrics.model_dump()
    results: dict[str, AcceptanceThresholdResult] = {}
    for name, minimum in ACCEPTANCE_MINIMUMS.items():
        value = values[name]
        passed = value >= minimum
        results[name] = AcceptanceThresholdResult(
            value=value,
            minimum=minimum,
            passed=passed,
            reason="" if passed else f"{value} < minimum {minimum}",
        )
    failed = tuple(sorted(name for name, result in results.items() if not result.passed))
    return ProductAcceptanceEvaluation(
        passed=not failed,
        thresholds=results,
        failed_metrics=failed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate scholarly product acceptance metrics")
    parser.add_argument("metrics", help="path to a JSON metrics object")
    args = parser.parse_args()
    metrics = ProductAcceptanceMetrics.model_validate_json(open(args.metrics, encoding="utf-8").read())
    evaluation = evaluate_product_acceptance(metrics)
    print(evaluation.model_dump_json(indent=2))
    raise SystemExit(0 if evaluation.passed else 1)


if __name__ == "__main__":
    main()


__all__ = [
    "ACCEPTANCE_MINIMUMS",
    "AcceptanceThresholdResult",
    "ProductAcceptanceEvaluation",
    "ProductAcceptanceMetrics",
    "evaluate_product_acceptance",
]
