"""LongBench v2 smoke adapter."""

from __future__ import annotations

import json
import os
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
    """Run LongBench v2 short smoke or return a medium-bucket blocked report."""

    bucket = request.bucket or "short"
    if bucket == "medium" and os.getenv("LONG_BENCH_ENABLE_MEDIUM") != "1":
        return _blocked_medium_bucket(request=request, descriptor=descriptor)

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    task_results = [_score_task(task) for task in task_specs]
    accuracy_overall = _average([float(row.official_metrics["accuracy"]) for row in task_results])
    accuracy_by_category = {
        task_results[0].metadata["category"]: accuracy_overall,
    }
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "accuracy_overall": accuracy_overall,
        "accuracy_by_bucket": {bucket: accuracy_overall},
        "accuracy_by_category": accuracy_by_category,
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "bucket": bucket,
        "truncation_rate": 0.0,
        "stage_runtime_seconds": {"adapter": 0.0},
        "task_count": len(task_results),
    }
    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=_role_for_bucket(bucket),
        status="completed",
        subset=request.subset or config.get("subset"),
        bucket=bucket,
        started_at=_utc_now(),
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path,
        dataset_manifest_path=config["dataset_manifest"],
        task_count=len(task_results),
        completed_count=len(task_results),
        official_metrics={
            "accuracy_overall": accuracy_overall,
            "accuracy_by_bucket": {bucket: accuracy_overall},
            "accuracy_by_category": accuracy_by_category,
        },
        internal_metrics={
            "truncation_rate": 0.0,
            "stage_runtime_seconds": {"adapter": 0.0},
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
            summary="LongBench v2 short smoke does not require a standalone integrity report.",
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


def _blocked_medium_bucket(*, request: BenchmarkRunRequest, descriptor) -> dict[str, Any]:
    note = "medium bucket requires a long-context backend; current local smoke run is blocked."
    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=descriptor.title,
        adapter_mode=descriptor.adapter_mode,
        role=_role_for_bucket("medium"),
        status="blocked",
        subset=request.subset,
        bucket="medium",
        started_at=_utc_now(),
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path or descriptor.config_path,
        dataset_manifest_path=None,
        task_count=0,
        completed_count=0,
        blocked_count=1,
        official_metrics={
            "accuracy_overall": None,
            "accuracy_by_bucket": {"medium": None},
            "accuracy_by_category": {},
        },
        internal_metrics={"truncation_rate": None, "stage_runtime_seconds": {}},
        notes=[note],
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "blocked_harness"},
    )
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "blocked",
        "accuracy_overall": None,
        "accuracy_by_bucket": {"medium": None},
        "accuracy_by_category": {},
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "bucket": "medium",
        "blocked_reason": note,
        "truncation_rate": None,
        "stage_runtime_seconds": {},
    }
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores=official_scores,
        internal_diagnostics=internal_diagnostics,
        task_results=[],
        integrity_report=BenchmarkIntegrityReport(
            benchmark=descriptor.benchmark,
            status="blocked",
            guards=list(descriptor.integrity_guards),
            summary=note,
        ),
    )
    return {
        "benchmark": descriptor.benchmark,
        "status": "blocked",
        "output_root": str(Path(request.output_root).resolve()),
        "artifacts": artifacts,
        "official_metrics": manifest.official_metrics,
        "internal_metrics": manifest.internal_metrics,
    }


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise ValueError("longbench_v2 requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _score_task(task: BenchmarkTaskSpec) -> BenchmarkTaskResult:
    correct_option = str(task.metadata.get("correct_option"))
    predicted_option = str(task.metadata.get("predicted_option"))
    accuracy = 1.0 if correct_option == predicted_option else 0.0
    return BenchmarkTaskResult(
        benchmark="longbench_v2",
        task_id=task.task_id,
        status="completed",
        prompt=task.prompt,
        prediction=predicted_option,
        expected_answer=correct_option,
        official_metrics={"accuracy": accuracy},
        internal_metrics={"truncation_rate": 0.0, "stage_runtime_seconds": {"adapter": 0.0}},
        notes=["Committed LongBench v2 short smoke fixture."],
        metadata=task.metadata,
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _role_for_bucket(bucket: str) -> str:
    return "external_regression" if bucket == "short" else "challenge_track"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
