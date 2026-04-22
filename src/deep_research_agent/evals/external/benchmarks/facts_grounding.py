"""FACTS Grounding open smoke adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from deep_research_agent.evals.external.contracts import (
    BenchmarkIntegrityReport,
    BenchmarkRunManifest,
    BenchmarkRunRequest,
    BenchmarkTaskResult,
    BenchmarkTaskSpec,
)
from deep_research_agent.evals.external.manifests import write_benchmark_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[5]


def run_benchmark(*, request: BenchmarkRunRequest, descriptor) -> dict[str, Any]:
    """Run the committed FACTS Grounding smoke fixture."""

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    started_at = _utc_now()
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    task_results = [_score_task(task) for task in task_specs]

    task_count = len(task_results)
    completed_count = len([row for row in task_results if row.status == "completed"])
    blocked_count = len([row for row in task_results if row.status == "blocked"])
    failed_count = len([row for row in task_results if row.status == "failed"])

    eligibility_score = _average(
        [
            float(row.official_metrics.get("eligibility_score", 0.0))
            for row in task_results
            if row.status == "completed"
        ]
    )
    grounding_score = _average(
        [
            float(row.official_metrics.get("grounding_score", 0.0))
            for row in task_results
            if row.status == "completed"
        ]
    )
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "score_version": "local_open_smoke_v1",
        "eligibility_score": eligibility_score,
        "grounding_score": grounding_score,
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "task_count": task_count,
        "completed_count": completed_count,
        "config_path": request.config_path,
        "dataset_manifest_path": config["dataset_manifest"],
        "adapter_mode": descriptor.adapter_mode,
        "role": descriptor.role,
        "critical_claim_support_precision": _average(
            [float(row.internal_metrics.get("critical_claim_support_precision", 0.0)) for row in task_results]
        ),
        "citation_error_rate": _average(
            [float(row.internal_metrics.get("citation_error_rate", 0.0)) for row in task_results]
        ),
        "provenance_completeness": _average(
            [float(row.internal_metrics.get("provenance_completeness", 0.0)) for row in task_results]
        ),
    }

    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="completed",
        split=request.split or config.get("split"),
        subset=request.subset or config.get("subset"),
        started_at=started_at,
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path,
        dataset_manifest_path=config["dataset_manifest"],
        task_count=task_count,
        completed_count=completed_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        official_metrics={
            "eligibility_score": eligibility_score,
            "grounding_score": grounding_score,
        },
        internal_metrics={
            "critical_claim_support_precision": internal_diagnostics["critical_claim_support_precision"],
            "citation_error_rate": internal_diagnostics["citation_error_rate"],
            "provenance_completeness": internal_diagnostics["provenance_completeness"],
        },
        notes=list(config.get("notes") or []),
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "local_fixture_smoke"},
    )
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores=official_scores,
        internal_diagnostics=internal_diagnostics,
        task_results=task_results,
        integrity_report=BenchmarkIntegrityReport(
            benchmark=descriptor.benchmark,
            status="not_applicable",
            guards=list(descriptor.integrity_guards),
            summary="FACTS Grounding open smoke does not emit a standalone integrity report in Phase 10.",
        ),
    )
    return {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "output_root": str(Path(request.output_root).resolve()),
        "artifacts": artifacts,
        "official_metrics": manifest.official_metrics,
        "internal_metrics": manifest.internal_metrics,
    }


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise ValueError("facts_grounding requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _score_task(task: BenchmarkTaskSpec) -> BenchmarkTaskResult:
    expected = task.expected_answer or ""
    prediction = task.prediction or ""
    exact_match = 1.0 if _normalize(expected) == _normalize(prediction) else 0.0
    token_f1 = _token_f1(expected, prediction)
    grounding_score = round((exact_match + token_f1) / 2.0, 6)
    citations = list(task.metadata.get("citations") or [])
    provenance_complete = bool(task.metadata.get("provenance_complete", False))
    return BenchmarkTaskResult(
        benchmark="facts_grounding",
        task_id=task.task_id,
        status="completed",
        prompt=task.prompt,
        prediction=prediction,
        expected_answer=expected,
        official_metrics={
            "eligibility_score": 1.0 if task.eligible else 0.0,
            "grounding_score": grounding_score,
        },
        internal_metrics={
            "critical_claim_support_precision": 1.0 if citations else 0.0,
            "citation_error_rate": 0.0 if citations else 1.0,
            "provenance_completeness": 1.0 if provenance_complete else 0.0,
        },
        notes=["Committed open smoke fixture for adapter/manifest validation."],
        metadata=task.metadata,
    )


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _token_f1(expected: str, prediction: str) -> float:
    expected_tokens = _normalize(expected).split()
    prediction_tokens = _normalize(prediction).split()
    if not expected_tokens and not prediction_tokens:
        return 1.0
    if not expected_tokens or not prediction_tokens:
        return 0.0
    overlap = 0
    remaining = list(prediction_tokens)
    for token in expected_tokens:
        if token in remaining:
            remaining.remove(token)
            overlap += 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(prediction_tokens)
    recall = overlap / len(expected_tokens)
    return round((2 * precision * recall) / (precision + recall), 6)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
