"""Run the Phase 05 low-cost local release smoke pack."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals import EVAL_SUITE_NAMES, run_eval_suite
from deep_research_agent.gateway.api import create_app
from deep_research_agent.gateway.cli import build_parser
from scripts.release_gate import build_release_gate_evidence, evaluate_release_gate, load_release_gate_config
from scripts.run_benchmark import build_benchmark_summary
from evaluation.comparators import load_topics


def run_release_smoke(*, output_root: str | Path) -> dict[str, Any]:
    resolved_output_root = Path(output_root).resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    suite_summaries = {
        suite_name: run_eval_suite(suite_name=suite_name, output_root=resolved_output_root / suite_name)
        for suite_name in EVAL_SUITE_NAMES
    }
    diagnostics = {
        "docs-public-surface": _docs_surface_diagnostic(),
        "api-contract-smoke": _api_contract_diagnostic(),
        "benchmark-diagnostics": _benchmark_diagnostic(),
    }
    evidence = build_release_gate_evidence(
        preflight={},
        full_benchmark_summary={},
        full_ablation_summary={},
        suite_summaries=suite_summaries,
        diagnostics=diagnostics,
    )
    config = load_release_gate_config()
    release_gate = evaluate_release_gate(evidence, config=config)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite_order": list(EVAL_SUITE_NAMES),
        "suites": suite_summaries,
        "evidence": evidence,
        "release_gate": release_gate,
    }
    manifest_path = resolved_output_root / "release_manifest.json"
    results_path = resolved_output_root / "RESULTS.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    results_path.write_text(_render_release_markdown(manifest), encoding="utf-8")
    return manifest


def _docs_surface_diagnostic() -> dict[str, Any]:
    help_text = build_parser().format_help()
    required_tokens = ("submit", "bundle", "eval")
    passed = all(token in help_text for token in required_tokens)
    return {
        "status": "passed" if passed else "failed",
        "required_tokens": list(required_tokens),
    }


def _api_contract_diagnostic() -> dict[str, Any]:
    schema = create_app().openapi()
    required_paths = {"/v1/research/jobs", "/v1/research/jobs/{job_id}", "/v1/batch/research"}
    passed = required_paths <= set(schema.get("paths") or {})
    return {
        "status": "passed" if passed else "failed",
        "required_paths": sorted(required_paths),
    }


def _benchmark_diagnostic() -> dict[str, Any]:
    topics = load_topics(topic_set="local3")
    summary = build_benchmark_summary(
        [
            {
                "topic_id": topics[0].id,
                "topic": topics[0].topic,
                "comparators": {
                    "ours": {
                        "status": "completed",
                        "success": True,
                        "metrics": {
                            "research_reliability_score_100": 88.0,
                            "system_controllability_score_100": 90.0,
                            "report_quality_score_100": 86.0,
                            "quality_gate_passed": True,
                            "time_seconds": 1.0,
                        },
                    }
                },
            }
        ]
    )
    return {
        "status": "passed" if summary["counts"]["completed"] >= 1 else "failed",
        "completed_topics": summary["counts"]["completed"],
        "topic_set": "local3",
    }


def _render_release_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Phase 5 Local Release Smoke",
        "",
        f"- release_gate: `{manifest['release_gate']['status']}`",
        "",
        "## Suites",
        "",
    ]
    for suite_name in manifest["suite_order"]:
        suite = manifest["suites"][suite_name]
        lines.append(f"- {suite_name}: `{suite['status']}`")
    lines.extend(["", "## Release Gate", ""])
    for reason in manifest["release_gate"].get("block_reasons", []):
        lines.append(f"- block: {reason}")
    if not manifest["release_gate"].get("block_reasons"):
        lines.append("- all required checks passed")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 5 local release smoke pack")
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(Path("evals") / "reports" / "phase5_local_smoke"),
        help="Directory for suite summaries and release manifest",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = run_release_smoke(output_root=args.output_root)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"release smoke: {manifest['release_gate']['status']} -> {Path(args.output_root).resolve() / 'release_manifest.json'}")


if __name__ == "__main__":
    main()
