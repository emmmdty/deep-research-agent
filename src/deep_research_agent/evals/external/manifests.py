"""Helpers for external benchmark artifact emission."""

from __future__ import annotations

import json
from pathlib import Path

from deep_research_agent.evals.external.contracts import (
    BenchmarkIntegrityReport,
    BenchmarkRunManifest,
    BenchmarkTaskResult,
)
from deep_research_agent.reporting.schemas import validate_instance


def write_benchmark_artifacts(
    *,
    output_root: Path,
    manifest: BenchmarkRunManifest,
    official_scores: dict[str, object],
    internal_diagnostics: dict[str, object],
    task_results: list[BenchmarkTaskResult],
    integrity_report: BenchmarkIntegrityReport | None = None,
) -> dict[str, str]:
    """Write the canonical artifact set for one benchmark run."""

    output_root.mkdir(parents=True, exist_ok=True)
    official_scores_path = output_root / "official_scores.json"
    diagnostics_path = output_root / "internal_diagnostics.json"
    task_results_path = output_root / "task_results.jsonl"
    readme_path = output_root / "README.md"
    manifest_path = output_root / "benchmark_run_manifest.json"
    integrity_path = output_root / "integrity_report.json"

    official_scores_path.write_text(json.dumps(official_scores, ensure_ascii=False, indent=2), encoding="utf-8")
    diagnostics_path.write_text(
        json.dumps(internal_diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    task_lines: list[str] = []
    for row in task_results:
        payload = row.model_dump(mode="json")
        validate_instance("benchmark-task-result", payload)
        task_lines.append(json.dumps(payload, ensure_ascii=False))
    task_results_path.write_text("\n".join(task_lines) + ("\n" if task_lines else ""), encoding="utf-8")

    if integrity_report is not None:
        integrity_payload = integrity_report.model_dump(mode="json")
        validate_instance("benchmark-integrity-report", integrity_payload)
        integrity_path.write_text(json.dumps(integrity_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.integrity_report = integrity_path.name

    manifest.artifacts = {
        "benchmark_run_manifest": manifest_path.name,
        "official_scores": official_scores_path.name,
        "internal_diagnostics": diagnostics_path.name,
        "task_results": task_results_path.name,
        "readme": readme_path.name,
    }
    if integrity_report is not None:
        manifest.artifacts["integrity_report"] = integrity_path.name

    manifest_payload = manifest.model_dump(mode="json")
    validate_instance("benchmark-run-manifest", manifest_payload)
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    readme_path.write_text(_render_readme(manifest, official_scores, internal_diagnostics), encoding="utf-8")
    return {name: str(output_root / filename) for name, filename in manifest.artifacts.items()}


def _render_readme(
    manifest: BenchmarkRunManifest,
    official_scores: dict[str, object],
    internal_diagnostics: dict[str, object],
) -> str:
    """Render a compact README sidecar for one benchmark run."""

    lines = [
        f"# {manifest.title}",
        "",
        f"- benchmark: `{manifest.benchmark}`",
        f"- status: `{manifest.status}`",
        f"- role: `{manifest.role}`",
        f"- adapter_mode: `{manifest.adapter_mode}`",
    ]
    if manifest.split:
        lines.append(f"- split: `{manifest.split}`")
    if manifest.subset:
        lines.append(f"- subset: `{manifest.subset}`")
    if manifest.bucket:
        lines.append(f"- bucket: `{manifest.bucket}`")
    lines.extend(
        [
            "",
            "## Official Scores",
            "",
            json.dumps(official_scores, ensure_ascii=False, indent=2),
            "",
            "## Internal Diagnostics",
            "",
            json.dumps(internal_diagnostics, ensure_ascii=False, indent=2),
            "",
        ]
    )
    return "\n".join(lines)
