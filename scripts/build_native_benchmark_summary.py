"""Build reviewer-facing native benchmark summary artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.native_benchmark import build_native_benchmark_summary as _build_native_benchmark_summary


def run_native_benchmark_summary(*, reports_root: str | Path, docs_root: str | Path) -> dict[str, Any]:
    return _build_native_benchmark_summary(reports_root=reports_root, docs_root=docs_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build native benchmark summary docs from committed regression artifacts")
    parser.add_argument(
        "--reports-root",
        default=str(Path("evals") / "reports" / "native_regression"),
        help="Directory that contains native regression release_manifest.json",
    )
    parser.add_argument(
        "--docs-root",
        default=str(Path("docs") / "benchmarks" / "native"),
        help="Directory that will receive README.md, NATIVE_SCORECARD.md, and CASEBOOK.md",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_native_benchmark_summary(reports_root=args.reports_root, docs_root=args.docs_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"native benchmark docs -> {Path(args.docs_root).resolve() / 'NATIVE_SCORECARD.md'}")


if __name__ == "__main__":
    main()
