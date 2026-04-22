"""LongFact / SAFE smoke adapter."""

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
    """Run the committed LongFact / SAFE smoke fixture."""

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    task_results = [_score_task(task) for task in task_specs]
    precision = _average([float(row.official_metrics["precision"]) for row in task_results])
    recall = _average([float(row.official_metrics["recall"]) for row in task_results])
    f1_at_k = _average([float(row.official_metrics["f1_at_k"]) for row in task_results])
    supported_fact_ratio = _average(
        [float(row.internal_metrics["supported_fact_ratio"]) for row in task_results]
    )
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "score_version": "local_smoke_v1",
        "precision": precision,
        "recall": recall,
        "f1_at_k": f1_at_k,
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "task_count": len(task_results),
        "config_path": request.config_path,
        "dataset_manifest_path": config["dataset_manifest"],
        "search_backend": config["search_backend"],
        "judge_backend": config["judge_backend"],
        "supported_fact_ratio": supported_fact_ratio,
        "latency_cost": {
            "estimated_api_cost": None,
            "judge_calls": 0,
            "search_calls": len(task_results),
        },
        "drift_risk": config["drift_risk"],
    }
    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="completed",
        subset=request.subset or config.get("subset"),
        started_at=_utc_now(),
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path,
        dataset_manifest_path=config["dataset_manifest"],
        task_count=len(task_results),
        completed_count=len(task_results),
        official_metrics={"precision": precision, "recall": recall, "f1_at_k": f1_at_k},
        internal_metrics={
            "supported_fact_ratio": supported_fact_ratio,
            "latency_cost": internal_diagnostics["latency_cost"],
        },
        notes=list(config.get("notes") or []),
        search_backend=config["search_backend"],
        judge_backend=config["judge_backend"],
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "local_fixture_smoke", "drift_risk": config["drift_risk"]},
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
            summary="Phase 11 logs search/judge backends in diagnostics; no separate integrity report is required.",
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
        raise ValueError("longfact_safe requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _score_task(task: BenchmarkTaskSpec) -> BenchmarkTaskResult:
    expected_facts = set(task.metadata.get("expected_facts") or [])
    predicted_facts = set(task.metadata.get("predicted_facts") or [])
    overlap = len(expected_facts & predicted_facts)
    precision = 1.0 if predicted_facts and overlap == len(predicted_facts) else overlap / max(len(predicted_facts), 1)
    recall = 1.0 if expected_facts and overlap == len(expected_facts) else overlap / max(len(expected_facts), 1)
    f1_at_k = 0.0 if not (precision + recall) else round((2 * precision * recall) / (precision + recall), 6)
    return BenchmarkTaskResult(
        benchmark="longfact_safe",
        task_id=task.task_id,
        status="completed",
        prompt=task.prompt,
        prediction=task.prediction,
        expected_answer=task.expected_answer,
        official_metrics={
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1_at_k": round(f1_at_k, 6),
        },
        internal_metrics={
            "supported_fact_ratio": 1.0 if expected_facts == predicted_facts else 0.0,
            "latency_cost": {"estimated_api_cost": None, "judge_calls": 0},
        },
        notes=["Committed LongFact/SAFE smoke fixture."],
        metadata=task.metadata,
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
