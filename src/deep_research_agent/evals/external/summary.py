"""Portfolio summary builder for the external benchmark layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from deep_research_agent.evals.external.contracts import BENCHMARK_NAMES, BenchmarkPortfolioSummary
from deep_research_agent.evals.external.registry import get_benchmark_descriptor
from deep_research_agent.reporting.schemas import validate_instance


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "evals" / "external" / "reports"
PORTFOLIO_GROUPS = {
    "authoritative_release_gate": ["native_phase5_local_smoke"],
    "secondary_regression": ["facts_grounding_open_smoke"],
    "external_regression": ["longfact_safe_smoke", "longbench_v2_short_smoke"],
    "challenge_track": ["browsecomp_guarded_smoke", "gaia_supported_subset", "longbench_v2_medium_long"],
    "deferred": [
        "browsecomp_full_1266",
        "facts_private_submission",
        "fully_measured_provider_routing_live_delta",
        "gaia_full_multimodal",
        "gaia_private_submission",
        "longbench_v2_full_submission",
        "longbench_v2_official_submission",
    ],
}
STATIC_RUN_IDS = {
    "facts_grounding": "facts_grounding_open_smoke",
    "longfact_safe": "longfact_safe_smoke",
    "longbench_v2": "longbench_v2_short_smoke",
    "browsecomp": "browsecomp_guarded_smoke",
    "gaia": "gaia_supported_subset",
}
STATIC_RUN_FIELDS = {
    "run_id",
    "title",
    "role",
    "adapter_mode",
    "split",
    "subset",
    "bucket",
    "config_path",
    "dataset_manifest_path",
    "dataset_task_count",
    "current_scope",
    "implementation_status",
    "integrity_guards",
    "notes",
    "search_backend",
    "judge_backend",
    "supported_capabilities",
}


def build_benchmark_portfolio_summary(
    *,
    output_root: str | Path,
    reports_root: str | Path | None = None,
) -> dict[str, object]:
    """Build the reviewer-facing benchmark portfolio summary artifacts."""

    output_root_path = Path(output_root).resolve()
    reports_root_path = Path(reports_root).resolve() if reports_root is not None else DEFAULT_REPORTS_ROOT.resolve()

    output_root_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_root_path / "portfolio_summary.json"
    readme_path = output_root_path / "README.md"

    run_rows = _build_static_run_rows()
    run_index = {_run_key(row): row for row in run_rows}

    discovered_paths = _discover_manifest_paths(reports_root=reports_root_path, output_root=output_root_path)
    for manifest_path in discovered_paths:
        manifest = _load_json(manifest_path)
        discovered_row = _row_from_run_manifest(manifest=manifest, manifest_path=manifest_path)
        key = _run_key(discovered_row)
        if key in run_index:
            existing = run_index[key]
            for field, value in discovered_row.items():
                if field in STATIC_RUN_FIELDS:
                    continue
                existing[field] = value
        else:
            discovered_row["implementation_status"] = "ad_hoc_run"
            run_index[key] = discovered_row
            run_rows.append(discovered_row)

    run_rows.sort(
        key=lambda row: (
            str(row.get("role") or ""),
            str(row.get("benchmark") or ""),
            str(row.get("split") or ""),
            str(row.get("bucket") or ""),
            str(row.get("subset") or ""),
        )
    )

    summary = BenchmarkPortfolioSummary(
        generated_at=datetime.now(timezone.utc).isoformat(),
        authoritative_release_gate=list(PORTFOLIO_GROUPS["authoritative_release_gate"]),
        secondary_regression=list(PORTFOLIO_GROUPS["secondary_regression"]),
        external_regression=list(PORTFOLIO_GROUPS["external_regression"]),
        challenge_track=list(PORTFOLIO_GROUPS["challenge_track"]),
        deferred=list(PORTFOLIO_GROUPS["deferred"]),
        runs=run_rows,
        notes=[
            "The authoritative release gate remains the native Phase 5 local smoke pack (`company12`, `industry12`, `trusted8`, `file8`, `recovery6`).",
            "FACTS Grounding is the current secondary regression track; it informs RC-style reporting without replacing the native release decision.",
            "LongFact / SAFE and LongBench v2 short are external regression tracks. BrowseComp, GAIA, and LongBench v2 medium/long remain informative challenge tracks only.",
            "This builder scans the reports root for concrete run manifests and overlays them onto the static adapter catalog, so blocked challenge runs are reported without fabricating scores.",
        ],
    )
    summary.artifacts = {
        "portfolio_summary": "portfolio_summary.json",
        "readme": "README.md",
    }

    payload = summary.model_dump(mode="json")
    previous_payload = _load_existing_summary(summary_path)
    if previous_payload is not None and _normalized_summary(previous_payload) == _normalized_summary(payload):
        payload["generated_at"] = previous_payload["generated_at"]
    validate_instance("benchmark-portfolio-summary", payload)

    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    readme_path.write_text(_render_summary_readme(payload), encoding="utf-8")

    return {
        "generated_at": payload["generated_at"],
        "output_root": str(output_root_path),
        "artifacts": {
            "portfolio_summary": str(summary_path),
            "readme": str(readme_path),
        },
        "run_count": len(run_rows),
        "discovered_run_count": len(discovered_paths),
    }


def _build_static_run_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for benchmark_name in BENCHMARK_NAMES:
        descriptor = get_benchmark_descriptor(benchmark_name)
        if not descriptor.config_path:
            continue

        config_path = PROJECT_ROOT / descriptor.config_path
        config = _load_yaml(config_path)
        dataset_manifest_path = PROJECT_ROOT / str(config["dataset_manifest"])
        dataset_manifest = _load_json(dataset_manifest_path)
        split = config.get("split") or dataset_manifest.get("split")
        subset = config.get("subset") or dataset_manifest.get("subset")
        bucket = config.get("bucket") or dataset_manifest.get("bucket")

        row: dict[str, object] = {
            "run_id": STATIC_RUN_IDS.get(benchmark_name, config_path.stem),
            "benchmark": descriptor.benchmark,
            "title": str(config.get("title") or descriptor.title),
            "role": descriptor.role,
            "adapter_mode": descriptor.adapter_mode,
            "split": split,
            "subset": subset,
            "bucket": bucket,
            "config_path": _repo_relative(config_path),
            "dataset_manifest_path": _repo_relative(dataset_manifest_path),
            "dataset_task_count": len(dataset_manifest.get("tasks", [])),
            "current_scope": _render_scope(split=split, subset=subset, bucket=bucket),
            "implementation_status": "implemented",
            "latest_run_status": "not_run",
            "integrity_guards": list(descriptor.integrity_guards),
            "notes": list(config.get("notes", [])),
        }
        for field in ("search_backend", "judge_backend", "supported_capabilities"):
            if field in config:
                row[field] = config[field]
        rows.append(row)
    return rows


def _discover_manifest_paths(*, reports_root: Path, output_root: Path) -> list[Path]:
    if not reports_root.exists():
        return []
    paths = []
    for path in sorted(reports_root.rglob("benchmark_run_manifest.json")):
        resolved = path.resolve()
        if resolved.is_relative_to(output_root):
            continue
        paths.append(resolved)
    return paths


def _row_from_run_manifest(*, manifest: dict[str, Any], manifest_path: Path) -> dict[str, object]:
    split = manifest.get("split")
    subset = manifest.get("subset")
    bucket = manifest.get("bucket")

    row: dict[str, object] = {
        "run_id": _compose_run_id(
            benchmark=str(manifest["benchmark"]),
            split=split,
            subset=subset,
            bucket=bucket,
        ),
        "benchmark": manifest["benchmark"],
        "title": manifest["title"],
        "role": manifest["role"],
        "adapter_mode": manifest["adapter_mode"],
        "split": split,
        "subset": subset,
        "bucket": bucket,
        "current_scope": _render_scope(split=split, subset=subset, bucket=bucket),
        "implementation_status": "discovered_run",
        "latest_run_status": manifest["status"],
        "latest_run_manifest": _repo_relative_or_absolute(manifest_path),
        "latest_output_root": _repo_relative_or_absolute(Path(str(manifest["output_root"]))),
        "task_count": manifest.get("task_count"),
        "completed_count": manifest.get("completed_count"),
        "blocked_count": manifest.get("blocked_count"),
        "failed_count": manifest.get("failed_count"),
        "official_metrics": manifest.get("official_metrics", {}),
        "internal_metrics": manifest.get("internal_metrics", {}),
        "integrity_report": manifest.get("integrity_report"),
        "integrity_guards": manifest.get("integrity_guards", []),
        "notes": manifest.get("notes", []),
    }
    if manifest.get("config_path"):
        row["config_path"] = _repo_relative_or_absolute(Path(str(manifest["config_path"])))
    if manifest.get("dataset_manifest_path"):
        row["dataset_manifest_path"] = _repo_relative_or_absolute(Path(str(manifest["dataset_manifest_path"])))
    return row


def _compose_run_id(
    *,
    benchmark: str,
    split: str | None,
    subset: str | None,
    bucket: str | None,
) -> str:
    parts = [benchmark]
    if split:
        parts.append(split)
    if bucket:
        parts.append(bucket)
    if subset:
        parts.append(subset)
    return "_".join(parts)


def _run_key(row: dict[str, object]) -> tuple[str, str | None, str | None, str | None]:
    return (
        str(row["benchmark"]),
        _optional_string(row.get("split")),
        _optional_string(row.get("subset")),
        _optional_string(row.get("bucket")),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _render_scope(*, split: object, subset: object, bucket: object) -> str:
    parts: list[str] = []
    if split:
        parts.append(f"split={split}")
    if subset:
        parts.append(f"subset={subset}")
    if bucket:
        parts.append(f"bucket={bucket}")
    return ", ".join(parts) if parts else "default"


def _render_summary_readme(summary: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Portfolio Summary",
        "",
        "The authoritative release gate remains the native Phase 5 local smoke pack (`company12`, `industry12`, `trusted8`, `file8`, `recovery6`).",
        "",
        "## Current Layering",
        "",
        f"- authoritative_release_gate: {', '.join(summary['authoritative_release_gate'])}",
        f"- secondary_regression: {', '.join(summary['secondary_regression'])}",
        f"- external_regression: {', '.join(summary['external_regression'])}",
        f"- challenge_track: {', '.join(summary['challenge_track'])}",
        f"- deferred: {', '.join(summary['deferred'])}",
        "",
        "## Current Runs",
        "",
    ]
    for run in summary["runs"]:
        lines.append(
            "- `{run_id}`: role=`{role}`, latest_run_status=`{latest_run_status}`, scope={scope}".format(
                run_id=run["run_id"],
                role=run["role"],
                latest_run_status=run.get("latest_run_status", "not_run"),
                scope=run.get("current_scope", "default"),
            )
        )
    lines.extend(["", "## Notes", ""])
    for note in summary["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _repo_relative_or_absolute(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _load_existing_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path)


def _normalized_summary(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["generated_at"] = "__stable__"
    return normalized
