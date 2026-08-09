"""Build the static demo-site data bundle from committed repository assets.

Every demo-site datum must trace back to a committed artifact in this repository:

- report bundles from evals/fixtures/runs/ and evals/reports/followup_metrics/
- benchmark evidence from evals/reports/
- competitor figures from docs/final/COMPETITIVE_LANDSCAPE.md (maintained manually)

Usage:
    uv run python scripts/build_demo_site_data.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_DATA = ROOT / "apps" / "demo-site" / "public" / "data"

ABLATION_SOURCE = ROOT / "evals" / "reports" / "followup_metrics" / "ablation_summary.md"

# Structured mirror of evals/reports/followup_metrics/ablation_summary.md.
# Keep in sync with that file; the demo-site JSON is generated from this table.
ABLATIONS = [
    {
        "id": "audit_on_vs_off",
        "name": "Audit gate",
        "scope": "company12/company-openai-surface",
        "key_delta": "unsupported claim leakage -> 1.0",
        "interpretation": "Without audit-grounded support edges, unsupported claim leakage rises while the fixture still completes.",
    },
    {
        "id": "strict_source_policy_vs_relaxed",
        "name": "Strict source policy",
        "scope": "trusted8/trusted-langgraph-brief",
        "key_delta": "policy compliance 1.0 -> 0.333",
        "interpretation": "Relaxing trusted-only enforcement keeps the bundle flowing but admits a source the strict policy would block.",
    },
    {
        "id": "evidence_first_vs_baseline_synthesis",
        "name": "Evidence-first synthesis",
        "scope": "company12/company-openai-surface",
        "key_delta": "citation error rate -> 1.0",
        "interpretation": "Removing evidence-first grounding erodes provenance and support quality immediately in the emitted bundle.",
    },
    {
        "id": "rerank_on_vs_off",
        "name": "Rerank / edge selection",
        "scope": "industry12/industry-agent-stack",
        "key_delta": "critical claim support precision 1.0 -> 0.5",
        "interpretation": "Disabling the rerank-like edge selection leaves a critical claim with only context-only evidence.",
    },
    {
        "id": "provider_auto_vs_manual",
        "name": "Provider auto-routing",
        "scope": "provider_router",
        "key_delta": "deterministic inspection only",
        "interpretation": "Auto-routing can be inspected deterministically, but this local follow-up run does not include live quality or billing comparisons.",
    },
    {
        "id": "new_runtime_vs_legacy",
        "name": "V2 runtime vs legacy",
        "scope": "runtime_control_plane",
        "key_delta": "not comparable",
        "interpretation": "No like-for-like legacy runtime fixture remains that matches the current deterministic job contracts and bundle outputs.",
    },
]


def copy_json(src: Path, dest_name: str) -> None:
    if not src.exists():
        raise SystemExit(f"missing source asset: {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    out = DEMO_DATA / dest_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"copied {src.relative_to(ROOT)} -> {out.relative_to(ROOT)}")


def main() -> None:
    fixtures = ROOT / "evals" / "fixtures" / "runs"
    reports = ROOT / "evals" / "reports"
    examples = ROOT / "examples" / "sample_bundle"
    docs = ROOT / "docs"

    shutil.rmtree(DEMO_DATA, ignore_errors=True)
    DEMO_DATA.mkdir(parents=True)

    for run_id in ("ths-20260522", "dsv4-20260425"):
        run_dir = fixtures / run_id
        if not run_dir.exists():
            raise SystemExit(f"missing fixture run: {run_dir}")
        target = DEMO_DATA / "runs" / run_id
        shutil.copytree(run_dir, target)
        print(f"copied {run_dir.relative_to(ROOT)} -> {target.relative_to(ROOT)}")

    copy_json(examples / "report_bundle.json", "runs/sample-bundle/report_bundle.json")

    copy_json(
        reports
        / "followup_metrics"
        / "company12_fresh"
        / "company-openai-surface"
        / "bundle"
        / "report_bundle.json",
        "runs/company-openai-surface/report_bundle.json",
    )

    copy_json(reports / "followup_metrics" / "headline_metrics.json", "benchmarks/headline_metrics.json")
    copy_json(reports / "phase5_local_smoke" / "release_manifest.json", "benchmarks/release_manifest.json")
    copy_json(
        reports / "followup_metrics" / "latency_cost_summary.json",
        "benchmarks/latency_cost_summary.json",
    )

    portfolio = reports.parent / "external" / "reports" / "portfolio_summary" / "portfolio_summary.json"
    copy_json(portfolio, "benchmarks/portfolio_summary.json")

    if not ABLATION_SOURCE.exists():
        raise SystemExit(f"missing ablation source: {ABLATION_SOURCE}")
    ablation_out = DEMO_DATA / "benchmarks" / "ablation_summary.json"
    ablation_out.write_text(
        json.dumps(
            {"source": str(ABLATION_SOURCE.relative_to(ROOT)), "ablations": ABLATIONS},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"generated {ablation_out.relative_to(ROOT)} (source: {ABLATION_SOURCE.relative_to(ROOT)})")

    assets = DEMO_DATA.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(docs / "assets" / "architecture-overview.png", assets / "architecture-overview.png")
    print("copied docs/assets/architecture-overview.png -> public/assets/")

    print("\ndone: apps/demo-site/public/data/")


if __name__ == "__main__":
    main()
