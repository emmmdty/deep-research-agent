"""Run BrowseComp guarded smoke."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.external import run_external_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BrowseComp guarded smoke")
    parser.add_argument("--subset", type=str, default="smoke", help="subset 名称")
    parser.add_argument("--config", type=str, default=None, help="可选配置路径")
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(Path("evals") / "external" / "reports" / "browsecomp_guarded_smoke"),
        help="输出目录",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_external_benchmark(
        benchmark_name="browsecomp",
        subset=args.subset,
        output_root=args.output_root,
        config_path=args.config,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"browsecomp: {result['status']} -> {Path(result['output_root']).resolve()}")


if __name__ == "__main__":
    main()
