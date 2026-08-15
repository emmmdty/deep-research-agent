"""Real GAIA 2023 validation runner for the canonical scheduler-v2 agent.

Runs the model-driven evidence-first agent (live LLM + governed web/GitHub/
arXiv search) on a frozen sample of the GAIA 2023 validation set (text-only
questions, no attachments), extracts an answer from the synthesized report, and
grades it against the ground truth with both exact-match and an LLM judge.

This is the live agent lane for the external benchmark portfolio: unlike the
guarded smoke adapters (``evals/external/benchmarks/gaia.py``), every question
here executes the real runtime against real providers and reports honest scores,
including per-question artifacts and error samples.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production \\
        uv run python scripts/run_gaia_real.py --max-questions 20

Chunked/resumable: pass ``--start-index`` / ``--max-questions``; questions whose
output directory already exists are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.live_benchmark_runner import (
    GAIA_JUDGE_SYSTEM,
    run_live_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    PROJECT_ROOT / "evals" / "external" / "dataset_manifests" / "gaia_2023_val_text_sample20.json"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "evals" / "reports" / "live_benchmarks" / "gaia_real"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run real GAIA 2023 validation questions")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--max-questions", type=int, default=20)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary = run_live_benchmark(
        manifest=manifest,
        out_dir=args.out_dir,
        judge_system=GAIA_JUDGE_SYSTEM,
        benchmark_label="GAIA 2023 validation (text-only sample)",
        start_index=args.start_index,
        max_questions=args.max_questions,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
