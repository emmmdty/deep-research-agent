"""CLI module for running one local eval suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from deep_research_agent.evals import EVAL_SUITE_NAMES
from deep_research_agent.evals.runner import run_eval_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one deterministic local eval suite")
    parser.add_argument("--suite", required=True, choices=EVAL_SUITE_NAMES)
    parser.add_argument("--output-root", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_eval_suite(suite_name=args.suite, output_root=args.output_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{args.suite}: {result['status']} -> {Path(result['summary_path'])}")


if __name__ == "__main__":
    main()
