"""Native regression benchmark runner and reviewer-facing summary builders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deep_research_agent.evals.contracts import EVAL_SUITE_NAMES
from deep_research_agent.evals.runner import run_eval_suite


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SMOKE_MANIFEST_PATH = PROJECT_ROOT / "evals" / "reports" / "phase5_local_smoke" / "release_manifest.json"
NATIVE_REPORTS_RELATIVE_ROOT = Path("evals") / "reports" / "native_regression"
NATIVE_DOCS_RELATIVE_ROOT = Path("docs") / "benchmarks" / "native"
FROZEN_NATIVE_REGRESSION_TIMESTAMP = "2026-04-22T00:00:00+00:00"
REGRESSION_VARIANT = "regression_local"
TARGET_TASK_COUNTS = {
    "company12": 12,
    "industry12": 12,
    "trusted8": 8,
    "file8": 8,
    "recovery6": 6,
}
SUITE_PURPOSES = {
    "company12": "Company profile and company-to-company comparison reasoning over frozen public materials.",
    "industry12": "Industry structure and segment-level comparison reasoning over deterministic public fixtures.",
    "trusted8": "Trusted-only research behavior with explicit allowlisted sources and no broad-web drift.",
    "file8": "Mixed public/private file ingest with provenance-preserving bundle emission.",
    "recovery6": "Runtime control-plane reliability for cancel, retry, resume, refine, and stale recovery.",
}
SMOKE_LOCAL_PROVES = [
    "The current merge-safe gate still passes on repo-local deterministic fixtures.",
    "The runtime, file ingest, source policy, claim audit, and recovery baseline all remain intact.",
    "The committed release smoke command and manifest contract still describe the authoritative release proof.",
]
REGRESSION_LOCAL_PROVES = [
    "The native benchmark surface expands from one-task demos into regression-tier suite coverage.",
    "Company, industry, trusted-only, file-ingest, and recovery/control-plane behavior all run at target suite counts.",
    "Reviewer-facing scorecard and casebook outputs can be regenerated from repo-local deterministic artifacts.",
]
STILL_NOT_COVERED = [
    "provider-backed full native execution remains out of scope for this deterministic local tier.",
    "Live web freshness, blind/private benchmark submissions, and one-off external benchmark integrations are intentionally excluded here.",
    "Multi-tenant deployment, auth, remote queues, and object storage remain outside the current local product boundary.",
]
AUTHORITATIVE_BOUNDARY_REASONS = [
    "It measures the repo's real product boundary: deterministic runtime, evidence-first bundles, source policy, file ingest, and recovery semantics.",
    "It runs entirely from repo-local frozen fixtures, so failures stay actionable and reproducible for this codebase.",
    "It reuses the same eval stack and manifest discipline as the existing smoke release gate instead of inventing a second benchmark system.",
]
CASEBOOK_SELECTION = {
    "company12": ["company-openai-platform", "company-openai-vs-anthropic"],
    "industry12": ["industry-agent-orchestration", "industry-durable-runtime"],
    "trusted8": ["trusted-langgraph-overview"],
    "file8": ["file-openai-private-brief"],
    "recovery6": ["stale_recovery"],
}


def run_native_regression(*, output_root: str | Path) -> dict[str, Any]:
    """Run the deterministic native regression layer and persist its manifest."""

    resolved_output_root = Path(output_root).resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    smoke_manifest = _load_json(SMOKE_MANIFEST_PATH)
    suite_summaries: dict[str, dict[str, Any]] = {}
    for suite_name in EVAL_SUITE_NAMES:
        summary = run_eval_suite(
            suite_name=suite_name,
            variant=REGRESSION_VARIANT,
            output_root=resolved_output_root / suite_name,
        )
        expected_task_count = TARGET_TASK_COUNTS[suite_name]
        if summary["task_count"] != expected_task_count:
            raise ValueError(
                f"native regression target mismatch for {suite_name}: expected {expected_task_count}, got {summary['task_count']}"
            )
        suite_summaries[suite_name] = summary

    suite_variants = {suite_name: REGRESSION_VARIANT for suite_name in EVAL_SUITE_NAMES}
    suite_statuses = {suite_name: summary["status"] for suite_name, summary in suite_summaries.items()}
    status = "passed" if all(value == "passed" for value in suite_statuses.values()) else "failed"
    manifest = {
        "generated_at": FROZEN_NATIVE_REGRESSION_TIMESTAMP,
        "benchmark_name": "native_regression",
        "status": status,
        "suite_order": list(EVAL_SUITE_NAMES),
        "suite_variants": suite_variants,
        "smoke_baseline_task_counts": {
            suite_name: int(smoke_manifest["suites"][suite_name]["task_count"]) for suite_name in EVAL_SUITE_NAMES
        },
        "regression_target_task_counts": dict(TARGET_TASK_COUNTS),
        "authoritative_merge_gate": {
            "name": "phase5_local_smoke",
            "status": smoke_manifest["release_gate"]["status"],
            "path": "evals/reports/phase5_local_smoke/release_manifest.json",
            "suite_order": smoke_manifest["suite_order"],
        },
        "coverage_contract": {
            suite_name: {
                "smoke_local_task_count": int(smoke_manifest["suites"][suite_name]["task_count"]),
                "regression_local_task_count": int(suite_summaries[suite_name]["task_count"]),
                "purpose": SUITE_PURPOSES[suite_name],
            }
            for suite_name in EVAL_SUITE_NAMES
        },
        "what_smoke_local_proves": list(SMOKE_LOCAL_PROVES),
        "what_regression_local_proves": list(REGRESSION_LOCAL_PROVES),
        "still_not_covered": list(STILL_NOT_COVERED),
        "authoritative_for_repo_boundary": list(AUTHORITATIVE_BOUNDARY_REASONS),
        "suites": suite_summaries,
    }

    manifest_path = resolved_output_root / "release_manifest.json"
    results_path = resolved_output_root / "RESULTS.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    results_path.write_text(_render_native_results_markdown(manifest), encoding="utf-8")
    return manifest


def build_native_benchmark_summary(*, reports_root: str | Path, docs_root: str | Path) -> dict[str, Any]:
    """Build reviewer-facing native benchmark docs and machine-readable summary."""

    resolved_reports_root = Path(reports_root).resolve()
    resolved_docs_root = Path(docs_root).resolve()
    resolved_reports_root.mkdir(parents=True, exist_ok=True)
    resolved_docs_root.mkdir(parents=True, exist_ok=True)

    manifest = _load_json(resolved_reports_root / "release_manifest.json")
    smoke_manifest = _load_json(SMOKE_MANIFEST_PATH)

    suite_matrix = {
        suite_name: {
            "smoke_local_task_count": int(smoke_manifest["suites"][suite_name]["task_count"]),
            "regression_local_task_count": int(manifest["suites"][suite_name]["task_count"]),
            "target_task_count": TARGET_TASK_COUNTS[suite_name],
            "status": manifest["suites"][suite_name]["status"],
            "purpose": SUITE_PURPOSES[suite_name],
            "key_metrics": _select_suite_metrics(suite_name, manifest["suites"][suite_name]["metrics"]),
        }
        for suite_name in EVAL_SUITE_NAMES
    }
    casebook_cases = _select_casebook_cases(manifest)
    summary = {
        "generated_at": manifest["generated_at"],
        "benchmark_name": "native_regression",
        "authoritative_merge_gate": {
            "name": "phase5_local_smoke",
            "path": "evals/reports/phase5_local_smoke/release_manifest.json",
            "status": smoke_manifest["release_gate"]["status"],
            "what_smoke_local_proves": list(SMOKE_LOCAL_PROVES),
        },
        "regression_layer": {
            "name": "native_regression_local",
            "path": "evals/reports/native_regression/release_manifest.json",
            "status": manifest["status"],
            "what_regression_local_proves": list(REGRESSION_LOCAL_PROVES),
        },
        "suite_matrix": suite_matrix,
        "coverage": {"still_not_covered": list(STILL_NOT_COVERED)},
        "authoritative_for_repo_boundary": list(AUTHORITATIVE_BOUNDARY_REASONS),
        "casebook": {"selected_cases": casebook_cases},
        "artifacts": {
            "release_manifest": "evals/reports/native_regression/release_manifest.json",
            "native_summary_json": "evals/reports/native_regression/native_summary.json",
            "results_markdown": "evals/reports/native_regression/RESULTS.md",
            "native_readme": "docs/benchmarks/native/README.md",
            "native_scorecard": "docs/benchmarks/native/NATIVE_SCORECARD.md",
            "casebook": "docs/benchmarks/native/CASEBOOK.md",
        },
    }

    native_summary_path = resolved_reports_root / "native_summary.json"
    readme_path = resolved_docs_root / "README.md"
    scorecard_path = resolved_docs_root / "NATIVE_SCORECARD.md"
    casebook_path = resolved_docs_root / "CASEBOOK.md"

    native_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    readme_path.write_text(_render_native_readme(summary), encoding="utf-8")
    scorecard_path.write_text(_render_native_scorecard(summary), encoding="utf-8")
    casebook_path.write_text(_render_casebook(summary), encoding="utf-8")

    return {"artifacts": summary["artifacts"]}


def _select_suite_metrics(suite_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    metric_order = {
        "company12": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "industry12": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "trusted8": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "file8": ("completion_rate", "bundle_emission_rate", "file_input_success_rate"),
        "recovery6": ("completion_rate", "resume_success_rate", "stale_recovery_success_rate"),
    }
    return {
        metric_name: metrics[metric_name]
        for metric_name in metric_order[suite_name]
        if metric_name in metrics
    }


def _select_casebook_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for suite_name, selected_ids in CASEBOOK_SELECTION.items():
        suite = manifest["suites"][suite_name]
        task_index = {
            (task.get("task_id") or task.get("scenario_id")): task
            for task in suite.get("tasks", [])
        }
        for selected_id in selected_ids:
            task = task_index[selected_id]
            case = {
                "suite_name": suite_name,
                "task_id": selected_id,
                "description": task.get("description") or task.get("topic") or task.get("title") or selected_id,
                "key_metrics": _case_metrics_for_suite(suite_name, suite, task),
                "conclusion": _case_conclusion_for_suite(suite_name, task),
            }
            if suite_name == "recovery6":
                case["report_path"] = "not applicable for reliability case"
                case["bundle_path"] = "not applicable for reliability case"
                case["summary_path"] = suite.get("summary_path", "evals/reports/native_regression/recovery6/summary.json")
            else:
                case["report_path"] = task["report_path"]
                case["bundle_path"] = task["bundle_path"]
            cases.append(case)
    return cases


def _case_metrics_for_suite(suite_name: str, suite: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    if suite_name == "recovery6":
        return {
            "passed": bool(task.get("passed", False)),
            "resume_success_rate": suite["metrics"].get("resume_success_rate"),
            "stale_recovery_success_rate": suite["metrics"].get("stale_recovery_success_rate"),
        }
    task_metrics = task.get("task_metrics") or {}
    metric_order = {
        "company12": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "industry12": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "trusted8": ("completion_rate", "bundle_emission_rate", "policy_compliance_rate"),
        "file8": ("completion_rate", "bundle_emission_rate", "file_input_success_rate", "policy_compliance_rate"),
    }
    return {
        key: task_metrics[key]
        for key in metric_order.get(suite_name, ("completion_rate", "bundle_emission_rate"))
        if key in task_metrics
    }


def _case_conclusion_for_suite(suite_name: str, task: dict[str, Any]) -> str:
    description = task.get("description") or task.get("topic") or task.get("title") or task.get("task_id") or task.get("scenario_id")
    if suite_name == "recovery6":
        return "This reliability case shows the control plane can clear stale worker state and resume deterministically without a report artifact."
    return f"{description} emits a grounded report bundle from deterministic native fixtures."


def _render_native_results_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Native Regression Benchmark",
        "",
        f"- status: `{manifest['status']}`",
        "- smoke_local remains the authoritative merge-safe gate.",
        "- regression_local expands reviewer-facing native coverage but does not replace the release smoke gate.",
        "",
        "## Suites",
        "",
    ]
    for suite_name in manifest["suite_order"]:
        coverage = manifest["coverage_contract"][suite_name]
        lines.append(
            f"- {suite_name}: `{manifest['suites'][suite_name]['status']}` "
            f"(smoke_local={coverage['smoke_local_task_count']}, regression_local={coverage['regression_local_task_count']})"
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- authoritative merge-safe gate: `evals/reports/phase5_local_smoke/release_manifest.json`",
            "- regression manifest: `evals/reports/native_regression/release_manifest.json`",
            "",
        ]
    )
    return "\n".join(lines)


def _render_native_readme(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Native Benchmark",
            "",
            "This directory contains the reviewer-facing documentation for the repo-native benchmark surface.",
            "",
            "Authoritative baseline:",
            "",
            "- `smoke_local` remains the authoritative merge-safe gate under `evals/reports/phase5_local_smoke/`.",
            "- `regression_local` expands deterministic native coverage under `evals/reports/native_regression/`.",
            "",
            "Key review artifacts:",
            "",
            "- `NATIVE_SCORECARD.md`",
            "- `CASEBOOK.md`",
            "- `evals/reports/native_regression/release_manifest.json`",
            "- `evals/reports/native_regression/native_summary.json`",
            "",
            "Rebuild commands:",
            "",
            "- `uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json`",
            "- `uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json`",
            "",
            "This layer stays deterministic and repo-local. It does not require provider secrets or external benchmark integration.",
            "",
        ]
    )


def _render_native_scorecard(summary: dict[str, Any]) -> str:
    lines = [
        "# Native Scorecard",
        "",
        "## What smoke_local proves",
        "",
    ]
    for item in summary["authoritative_merge_gate"]["what_smoke_local_proves"]:
        lines.append(f"- {item}")
    lines.extend(["", "## What regression_local proves", ""])
    for item in summary["regression_layer"]["what_regression_local_proves"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Suite Matrix", "", "| Suite | smoke_local | regression_local | status | What it adds |", "| --- | ---: | ---: | --- | --- |"])
    for suite_name in EVAL_SUITE_NAMES:
        row = summary["suite_matrix"][suite_name]
        lines.append(
            f"| `{suite_name}` | `{row['smoke_local_task_count']}` | `{row['regression_local_task_count']}` | "
            f"`{row['status']}` | {row['purpose']} |"
        )
    lines.extend(["", "## What is still not covered", ""])
    for item in summary["coverage"]["still_not_covered"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Why this benchmark is authoritative for this repo's product boundary", ""])
    for item in summary["authoritative_for_repo_boundary"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _render_casebook(summary: dict[str, Any]) -> str:
    lines = [
        "# Native Casebook",
        "",
        "These cases are selected from the deterministic native regression artifacts and are intended for reviewer inspection.",
        "",
    ]
    for case in summary["casebook"]["selected_cases"]:
        lines.extend(
            [
                f"## {case['suite_name']} / {case['task_id']}",
                "",
                f"- suite name: `{case['suite_name']}`",
                f"- task id: `{case['task_id']}`",
                f"- one-line task description: {case['description']}",
                f"- report path: `{case['report_path']}`",
                f"- bundle path: `{case['bundle_path']}`",
            ]
        )
        if case.get("summary_path"):
            lines.append(f"- summary path: `{case['summary_path']}`")
        metrics_text = ", ".join(f"{key}={value}" for key, value in case["key_metrics"].items())
        lines.extend(
            [
                f"- key metrics: `{metrics_text}`",
                f"- conclusion: {case['conclusion']}",
                "",
            ]
        )
    return "\n".join(lines)


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).resolve().read_text(encoding="utf-8"))
