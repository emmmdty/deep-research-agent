"""Build the native optimization-cycle comparison artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.native_optimization import build_native_optimization_summary as _build_native_optimization_summary


def run_native_optimization_summary(
    *,
    baseline_tag: str,
    reports_root: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    return _build_native_optimization_summary(
        baseline_tag=baseline_tag,
        reports_root=reports_root,
        output_root=output_root,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build native optimization before/after artifacts from regression reports")
    parser.add_argument("--baseline-tag", required=True, help="Annotated local baseline tag for the optimization cycle")
    parser.add_argument(
        "--reports-root",
        default=str(Path("evals") / "reports" / "native_regression"),
        help="Directory that contains native regression artifacts",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path("evals") / "reports" / "native_optimization"),
        help="Directory that will receive optimization_summary.json and BEFORE_AFTER.md",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_native_optimization_summary(
        baseline_tag=args.baseline_tag,
        reports_root=args.reports_root,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"native optimization summary -> {Path(args.output_root).resolve() / 'optimization_summary.json'}")


if __name__ == "__main__":
    main()
