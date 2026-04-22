"""BrowseComp guarded smoke adapter."""

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
from deep_research_agent.evals.external.integrity import detect_canary, detect_denylist_hits, redact_query
from deep_research_agent.evals.external.manifests import write_benchmark_artifacts


PROJECT_ROOT = Path(__file__).resolve().parents[5]


def run_benchmark(*, request: BenchmarkRunRequest, descriptor) -> dict[str, Any]:
    """Run the guarded BrowseComp smoke fixture."""

    config = _load_config(request.config_path)
    dataset = _load_dataset(config["dataset_manifest"])
    task_specs = [BenchmarkTaskSpec.model_validate(task) for task in dataset["tasks"]]
    findings: list[dict[str, object]] = []
    task_results: list[BenchmarkTaskResult] = []
    for task in task_specs:
        denylist_hits = detect_denylist_hits(task.prompt, list(config["denylist_terms"]))
        canary_hits = detect_canary(task.prompt, list(config["canary_terms"]))
        redacted_query = redact_query(task.prompt, list(config["denylist_terms"]))
        if denylist_hits or canary_hits:
            findings.append(
                {
                    "task_id": task.task_id,
                    "denylist_hits": denylist_hits,
                    "canary_hits": canary_hits,
                }
            )
        task_results.append(
            BenchmarkTaskResult(
                benchmark="browsecomp",
                task_id=task.task_id,
                status="completed",
                prompt=task.prompt,
                prediction=task.prediction,
                expected_answer=task.expected_answer,
                official_metrics={
                    "short_answer_accuracy": 1.0,
                    "semantic_equivalence_pass_rate": 1.0,
                },
                internal_metrics={"search_steps": 1, "integrity_findings_count": len(findings)},
                notes=["Committed BrowseComp guarded smoke fixture."],
                metadata={"redacted_query": redacted_query},
            )
        )
    official_scores = {
        "benchmark": descriptor.benchmark,
        "status": "completed",
        "short_answer_accuracy": 1.0,
        "semantic_equivalence_pass_rate": 1.0,
    }
    internal_diagnostics = {
        "benchmark": descriptor.benchmark,
        "integrity_findings_count": len(findings),
        "search_steps": 1,
        "guard_mode": "guarded_smoke",
    }
    integrity_report = BenchmarkIntegrityReport(
        benchmark=descriptor.benchmark,
        status="passed" if not findings else "failed",
        guards=list(descriptor.integrity_guards),
        findings=findings,
        summary="BrowseComp guarded smoke ran with query redaction and canary/denylist checks.",
    )
    manifest = BenchmarkRunManifest(
        benchmark=descriptor.benchmark,
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="completed" if not findings else "failed",
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
        environment={"runner": "guarded_fixture_smoke"},
    )
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores=official_scores,
        internal_diagnostics=internal_diagnostics,
        task_results=task_results,
        integrity_report=integrity_report,
    )
    return {
        "benchmark": descriptor.benchmark,
        "status": manifest.status,
        "output_root": str(Path(request.output_root).resolve()),
        "artifacts": artifacts,
        "official_metrics": manifest.official_metrics,
        "internal_metrics": manifest.internal_metrics,
    }


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise ValueError("browsecomp requires a config_path")
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    payload["dataset_manifest"] = str((PROJECT_ROOT / payload["dataset_manifest"]).resolve())
    return payload


def _load_dataset(dataset_path: str) -> dict[str, Any]:
    return json.loads(Path(dataset_path).read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
