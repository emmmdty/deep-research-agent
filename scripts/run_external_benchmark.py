"""Run one external benchmark through the shared adapter substrate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.external import BENCHMARK_NAMES, run_external_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one external benchmark")
    parser.add_argument("--benchmark", required=True, choices=BENCHMARK_NAMES, help="benchmark 名称")
    parser.add_argument("--split", type=str, default=None, help="benchmark split，例如 open")
    parser.add_argument("--subset", type=str, default="smoke", help="subset 名称，例如 smoke")
    parser.add_argument("--bucket", type=str, default=None, help="可选 bucket")
    parser.add_argument("--config", type=str, default=None, help="可选配置文件路径")
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="输出目录，默认写到 evals/external/reports/<benchmark>_<subset>",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output_root = args.output_root or str(Path("evals") / "external" / "reports" / f"{args.benchmark}_{args.subset}")
    result = run_external_benchmark(
        benchmark_name=args.benchmark,
        split=args.split,
        subset=args.subset,
        bucket=args.bucket,
        output_root=output_root,
        config_path=args.config,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{args.benchmark}: {result['status']} -> {Path(result['output_root']).resolve()}")


if __name__ == "__main__":
    main()
