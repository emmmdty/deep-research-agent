"""Build the reviewer-facing benchmark portfolio summary artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.external import build_benchmark_portfolio_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the benchmark portfolio summary")
    parser.add_argument(
        "--reports-root",
        type=str,
        default=str(Path("evals") / "external" / "reports"),
        help="扫描 benchmark_run_manifest.json 的目录",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(Path("evals") / "external" / "reports" / "portfolio_summary"),
        help="输出目录",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_benchmark_portfolio_summary(
        output_root=args.output_root,
        reports_root=args.reports_root,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"portfolio_summary -> {Path(result['artifacts']['portfolio_summary']).resolve()}")


if __name__ == "__main__":
    main()
