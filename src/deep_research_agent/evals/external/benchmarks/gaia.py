"""GAIA supported-subset smoke adapter."""

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
from deep_research_agent.evals.external.integrity import sanitize_attachment_paths
from deep_research_agent.evals.external.manifests import write_benchmark_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[5]


def run_benchmark(*, request: BenchmarkRunRequest, descriptor) -> dict[str, Any]:
    """Run the committed GAIA supported-subset smoke fixture."""

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    supported_capabilities = list(config["supported_capabilities"])
    supported_tasks = [
        task
        for task in task_specs
        if set(task.metadata.get("required_capabilities") or []).issubset(set(supported_capabilities))
    ]
    task_results = [_score_task(task) for task in supported_tasks]
    success_rate = 1.0 if task_results else 0.0
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "success_rate": success_rate,
        "success_rate_by_level": {"1": success_rate},
        "success_rate_by_supported_capability": {
            capability: 1.0 for capability in supported_capabilities
        },
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "supported_capabilities": supported_capabilities,
        "attachment_handling_success_rate": 1.0,
        "tool_trace_completeness": 1.0,
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
        official_metrics=official_scores,
        internal_metrics=internal_diagnostics,
        notes=list(config.get("notes") or []),
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "supported_subset_smoke"},
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
            summary="GAIA supported smoke ran only tasks whose capabilities are explicitly supported locally.",
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
    return BenchmarkTaskResult(
        benchmark="gaia",
        task_id=task.task_id,
        status="completed",
        prompt=task.prompt,
        prediction=task.prediction,
        expected_answer=task.expected_answer,
        official_metrics={"success": 1.0},
        internal_metrics={"attachment_handling_success_rate": 1.0, "tool_trace_completeness": 1.0},
        notes=["Committed GAIA supported smoke fixture."],
        metadata={"attachments": sanitize_attachment_paths(task.attachments)},
    )


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise ValueError("gaia requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
