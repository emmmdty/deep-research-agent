"""Helpers for the focused native benchmark optimization cycle."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASEBOOK_PATH = PROJECT_ROOT / "docs" / "benchmarks" / "native" / "CASEBOOK.md"
INDUSTRY12_SUMMARY_RELATIVE_PATH = Path("evals") / "reports" / "native_regression" / "industry12" / "summary.json"
OPTIMIZATION_OUTPUT_RELATIVE_ROOT = Path("evals") / "reports" / "native_optimization"
SELECTED_TARGET = "industry12_discriminativeness"


def compute_industry12_discriminativeness_metrics(
    *,
    reports_root: str | Path,
    casebook_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compute the hardening metrics for the industry12 regression suite."""

    resolved_reports_root = Path(reports_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else resolved_reports_root.parents[2]
    resolved_casebook_path = Path(casebook_path or (resolved_repo_root / DEFAULT_CASEBOOK_PATH.relative_to(PROJECT_ROOT))).resolve()
    summary = _load_json(resolved_reports_root / "industry12" / "summary.json")
    casebook_text = resolved_casebook_path.read_text(encoding="utf-8")
    return _compute_metrics_from_summary(
        summary,
        casebook_text=casebook_text,
        bundle_loader=lambda bundle_ref: _load_json(_resolve_bundle_path(bundle_ref, repo_root=resolved_repo_root)),
    )


def load_industry12_discriminativeness_metrics_from_git_tag(
    *,
    baseline_tag: str,
    repo_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Load the same hardening metrics from a tagged git baseline."""

    resolved_repo_root = Path(repo_root).resolve()
    summary = _load_json_from_git_ref(
        baseline_tag,
        INDUSTRY12_SUMMARY_RELATIVE_PATH,
        repo_root=resolved_repo_root,
    )
    casebook_text = _load_text_from_git_ref(
        baseline_tag,
        DEFAULT_CASEBOOK_PATH.relative_to(PROJECT_ROOT),
        repo_root=resolved_repo_root,
    )
    return _compute_metrics_from_summary(
        summary,
        casebook_text=casebook_text,
        bundle_loader=lambda bundle_ref: _load_json_from_git_ref(
            baseline_tag,
            Path(bundle_ref),
            repo_root=resolved_repo_root,
        ),
    )


def resolve_git_ref(ref: str, *, repo_root: str | Path = PROJECT_ROOT) -> str:
    """Resolve a git ref to a full commit SHA."""

    resolved_repo_root = Path(repo_root).resolve()
    return (
        subprocess.run(
            ["git", "-C", str(resolved_repo_root), "rev-list", "-n", "1", ref],
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )


def build_native_optimization_summary(
    *,
    baseline_tag: str,
    reports_root: str | Path,
    output_root: str | Path,
    casebook_path: str | Path | None = None,
    repo_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Write the machine-readable and reviewer-facing before/after optimization summaries."""

    resolved_repo_root = Path(repo_root).resolve()
    resolved_reports_root = Path(reports_root).resolve()
    resolved_output_root = Path(output_root).resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    resolved_casebook_path = Path(casebook_path or (resolved_repo_root / DEFAULT_CASEBOOK_PATH.relative_to(PROJECT_ROOT))).resolve()

    baseline_commit = resolve_git_ref(baseline_tag, repo_root=resolved_repo_root)
    post_change_commit = resolve_git_ref("HEAD", repo_root=resolved_repo_root)
    baseline_metrics = load_industry12_discriminativeness_metrics_from_git_tag(
        baseline_tag=baseline_tag,
        repo_root=resolved_repo_root,
    )
    post_change_metrics = compute_industry12_discriminativeness_metrics(
        reports_root=resolved_reports_root,
        casebook_path=resolved_casebook_path,
        repo_root=resolved_repo_root,
    )
    deltas = _build_deltas(baseline_metrics, post_change_metrics)
    artifact_paths = {
        "baseline_industry12_summary": _display_path(INDUSTRY12_SUMMARY_RELATIVE_PATH, repo_root=resolved_repo_root),
        "post_industry12_summary": _display_path(resolved_reports_root / "industry12" / "summary.json", repo_root=resolved_repo_root),
        "post_casebook": _display_path(resolved_casebook_path, repo_root=resolved_repo_root),
        "optimization_summary": _display_path(resolved_output_root / "optimization_summary.json", repo_root=resolved_repo_root),
        "before_after_markdown": _display_path(resolved_output_root / "BEFORE_AFTER.md", repo_root=resolved_repo_root),
    }
    interpretation = _build_interpretation(baseline_metrics, post_change_metrics)

    summary = {
        "baseline_commit": baseline_commit,
        "baseline_tag": baseline_tag,
        "post_change_commit": post_change_commit,
        "selected_target": SELECTED_TARGET,
        "baseline_metrics": baseline_metrics,
        "post_change_metrics": post_change_metrics,
        "deltas": deltas,
        "interpretation": interpretation,
        "artifact_paths": artifact_paths,
    }

    summary_path = resolved_output_root / "optimization_summary.json"
    before_after_path = resolved_output_root / "BEFORE_AFTER.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    before_after_path.write_text(_render_before_after_markdown(summary), encoding="utf-8")

    return {"artifacts": {"optimization_summary": artifact_paths["optimization_summary"], "before_after_markdown": artifact_paths["before_after_markdown"]}}


def _compute_metrics_from_summary(
    summary: dict[str, Any],
    *,
    casebook_text: str,
    bundle_loader: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    tasks = list(summary.get("tasks") or [])
    conflict_case_count = 0
    multi_claim_task_count = 0
    uncertainty_case_count = 0

    for task in tasks:
        bundle = bundle_loader(str(task["bundle_path"]))
        claims = list(bundle.get("claims") or [])
        conflicts = list(bundle.get("conflict_sets") or [])
        if conflicts:
            conflict_case_count += 1
        if len(claims) > 1:
            multi_claim_task_count += 1
        if any(str(claim.get("uncertainty") or "") in {"medium", "high"} for claim in claims):
            uncertainty_case_count += 1

    return {
        "industry12_suite_status": str(summary.get("status") or "unknown"),
        "industry12_task_count": int(summary.get("task_count") or len(tasks)),
        "industry12_conflict_case_count": conflict_case_count,
        "industry12_multi_claim_task_count": multi_claim_task_count,
        "industry12_uncertainty_case_count": uncertainty_case_count,
        "industry12_casebook_conflict_example_present": "industry-governance-policy" in casebook_text,
    }


def _build_deltas(baseline_metrics: dict[str, Any], post_change_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    deltas: dict[str, dict[str, Any]] = {}
    for key, before in baseline_metrics.items():
        after = post_change_metrics[key]
        if isinstance(before, bool):
            delta: Any = after
        elif isinstance(before, (int, float)) and isinstance(after, (int, float)):
            delta = after - before
        else:
            delta = "changed" if after != before else "unchanged"
        deltas[key] = {"before": before, "after": after, "delta": delta}
    return deltas


def _build_interpretation(baseline_metrics: dict[str, Any], post_change_metrics: dict[str, Any]) -> str:
    if (
        post_change_metrics["industry12_suite_status"] == "passed"
        and post_change_metrics["industry12_task_count"] == baseline_metrics["industry12_task_count"]
        and post_change_metrics["industry12_conflict_case_count"] > baseline_metrics["industry12_conflict_case_count"]
        and post_change_metrics["industry12_multi_claim_task_count"] > baseline_metrics["industry12_multi_claim_task_count"]
        and post_change_metrics["industry12_uncertainty_case_count"] > baseline_metrics["industry12_uncertainty_case_count"]
    ):
        return (
            "industry12 bundle structure is now meaningfully conflict-aware while keeping the suite passing and the task count unchanged."
        )
    if post_change_metrics["industry12_suite_status"] != "passed":
        return "industry12 discriminativeness increased, but the suite no longer passes and needs follow-up."
    return "industry12 changed, but the hardening signal is mixed or inconclusive."


def _render_before_after_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Native Optimization Before/After",
        "",
        f"- baseline tag: `{summary['baseline_tag']}`",
        f"- baseline commit: `{summary['baseline_commit']}`",
        f"- post-change commit: `{summary['post_change_commit']}`",
        f"- selected target: `{summary['selected_target']}`",
        "",
        "## Deltas",
        "",
        "| Metric | Before | After | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, payload in summary["deltas"].items():
        lines.append(
            f"| `{key}` | `{payload['before']}` | `{payload['after']}` | `{payload['delta']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "## Quick Scan",
            "",
        ]
    )
    for key, payload in summary["deltas"].items():
        lines.append(f"- `{key}`: {payload['before']} -> {payload['after']}")
    return "\n".join(lines) + "\n"


def _resolve_bundle_path(bundle_ref: str, *, repo_root: Path) -> Path:
    candidate = Path(bundle_ref)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _display_path(path: str | Path, *, repo_root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_from_git_ref(ref: str, path: Path, *, repo_root: Path) -> dict[str, Any]:
    return json.loads(_load_text_from_git_ref(ref, path, repo_root=repo_root))


def _load_text_from_git_ref(ref: str, path: Path, *, repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{ref}:{path.as_posix()}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
