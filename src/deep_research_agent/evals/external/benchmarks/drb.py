"""DRB (Deep Research Bench) open smoke adapter.

Scoring modes align with the DRB paper (arXiv:2506.06287, FutureSearch)
Table 3: binary for number/source tasks, recall for list-hunting tasks,
F1 for reference-class/dataset compilation, absolute-difference for
claim validation. The smoke subset runs exclusively on the committed
offline fixture — no live web and no RetroSearch corpus access.
"""

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

LIST_MODES = ("recall", "f1")
LIST_SEPARATOR = "|"


def run_benchmark(*, request: BenchmarkRunRequest, descriptor) -> dict[str, Any]:
    """Run the committed DRB smoke subset fixture offline."""

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    started_at = _utc_now()
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    task_results = [_score_task(task) for task in task_specs]

    task_count = len(task_results)
    completed_count = len([row for row in task_results if row.status == "completed"])
    blocked_count = len([row for row in task_results if row.status == "blocked"])
    failed_count = len([row for row in task_results if row.status == "failed"])

    completed = [row for row in task_results if row.status == "completed"]
    task_scores = [float(row.official_metrics.get("task_score", 0.0)) for row in completed]
    overall_score = _average(task_scores)
    success_rate = _average([1.0 if score >= 1.0 else 0.0 for score in task_scores])

    category_scores: dict[str, list[float]] = {}
    for row in completed:
        category = str(row.metadata.get("category") or "unknown")
        category_scores.setdefault(category, []).append(
            float(row.official_metrics.get("task_score", 0.0))
        )

    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "score_version": config.get("score_version", "drb_local_smoke_v1"),
        "task_score": overall_score,
        "success_rate": success_rate,
        "task_score_by_category": {
            category: _average(values) for category, values in sorted(category_scores.items())
        },
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "task_count": task_count,
        "completed_count": completed_count,
        "blocked_count": blocked_count,
        "failed_count": failed_count,
        "config_path": request.config_path,
        "dataset_manifest_path": config["dataset_manifest"],
        "adapter_mode": descriptor.adapter_mode,
        "role": descriptor.role,
        "corpus_mode": "fixture_only_offline",
        "offline": True,
        "category_task_counts": {
            category: len(values) for category, values in category_scores.items()
        },
    }
    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="completed",
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
        official_metrics=official_scores,
        internal_metrics=internal_diagnostics,
        notes=list(config.get("notes") or []),
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "fixture_only_smoke", "corpus": "offline"},
    )
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores=official_scores,
        internal_diagnostics=internal_diagnostics,
        task_results=task_results,
        integrity_report=BenchmarkIntegrityReport(
            benchmark=descriptor.benchmark,
            status="passed",
            guards=list(descriptor.integrity_guards),
            summary="DRB smoke ran exclusively on the committed offline fixture; "
            "no live web or RetroSearch corpus access was made.",
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


def _score_task(task: BenchmarkTaskSpec) -> BenchmarkTaskResult:
    task_type = str(task.metadata.get("task_type") or "binary")
    mode = str(task.metadata.get("score_mode") or _default_mode(task_type))
    expected = task.expected_answer or ""
    prediction = task.prediction or ""
    score = _score_for_mode(mode, expected, prediction)
    return BenchmarkTaskResult(
        benchmark="drb",
        task_id=task.task_id,
        status="completed",
        prompt=task.prompt,
        prediction=prediction,
        expected_answer=expected,
        official_metrics={
            "task_type": task_type,
            "score_mode": mode,
            "task_score": score,
        },
        internal_metrics={
            "category": str(task.metadata.get("category") or "unknown"),
            "offline_corpus": bool(task.metadata.get("offline_corpus", True)),
        },
        notes=["Committed DRB smoke fixture; scored deterministically without live web access."],
        metadata=task.metadata,
    )


def _default_mode(task_type: str) -> str:
    if task_type in {"find_dataset", "gather_evidence"}:
        return "recall"
    if task_type in {"populate_reference_class", "compile_dataset"}:
        return "f1"
    if task_type == "validate_claim":
        return "difference"
    return "binary"


def _score_for_mode(mode: str, expected: str, prediction: str) -> float:
    if mode in LIST_MODES:
        expected_items = _split_items(expected)
        prediction_items = _split_items(prediction)
        if not expected_items:
            return 1.0
        if not prediction_items:
            return 0.0
        matched = sum(1 for item in expected_items if item in prediction_items)
        recall = matched / len(expected_items)
        if mode == "recall":
            return round(recall, 6)
        precision = matched / len(prediction_items)
        if recall == 0.0 and precision == 0.0:
            return 0.0
        return round((2 * precision * recall) / (precision + recall), 6)
    if mode == "difference":
        try:
            # 偏差越大得分越低，但必须夹在 [0,1]：prediction 远离 expected 时
            # 原始公式会产出负分，污染 task_score/分类均分/head-to-head delta。
            return round(max(0.0, 1.0 - abs(float(prediction) - float(expected))), 6)
        except (TypeError, ValueError):
            return 0.0
    return 1.0 if _normalize(expected) == _normalize(prediction) else 0.0


def _split_items(value: str) -> list[str]:
    return [item.strip() for item in value.split(LIST_SEPARATOR) if item.strip()]


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise ValueError("drb requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
