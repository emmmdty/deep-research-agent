"""Real BrowseComp runner for the canonical scheduler-v2 agent.

Runs the model-driven evidence-first agent (live LLM + governed web/GitHub/
arXiv search) on a frozen stratified sample of the BrowseComp dataset
(1266 official questions, sourced via an ungated mirror with the same
canary-keyed payloads), extracts an answer from the synthesized report, and
grades it with exact match plus an LLM judge.

This is the live agent lane for the external benchmark portfolio: unlike the
guarded smoke adapter (``evals/external/benchmarks/browsecomp.py``), every
question here executes the real runtime against real providers and reports
honest scores with committed per-question artifacts and error samples.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production \\
        uv run python scripts/run_browsecomp_real.py --max-questions 15

Chunked/resumable: pass ``--start-index`` / ``--max-questions``; questions whose
output directory already exists are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.live_benchmark_runner import (  # noqa: E402
    BROWSECOMP_JUDGE_SYSTEM,
    run_live_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    PROJECT_ROOT / "evals" / "external" / "dataset_manifests" / "browsecomp_sample15.json"
)
DEFAULT_OUT_DIR = (
    PROJECT_ROOT / "evals" / "reports" / "live_benchmarks" / "browsecomp_real"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run real BrowseComp questions")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--max-questions", type=int, default=15)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary = run_live_benchmark(
        manifest=manifest,
        out_dir=args.out_dir,
        judge_system=BROWSECOMP_JUDGE_SYSTEM,
        benchmark_label="BrowseComp (stratified sample)",
        start_index=args.start_index,
        max_questions=args.max_questions,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
