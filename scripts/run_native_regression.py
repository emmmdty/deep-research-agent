"""Run the deterministic native regression benchmark surface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.native_benchmark import run_eval_suite as _canonical_run_eval_suite
from deep_research_agent.evals import native_benchmark


run_eval_suite = _canonical_run_eval_suite


def run_native_regression(*, output_root: str | Path) -> dict[str, Any]:
    native_benchmark.run_eval_suite = run_eval_suite
    return native_benchmark.run_native_regression(output_root=output_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic native regression benchmark")
    parser.add_argument(
        "--output-root",
        default=str(Path("evals") / "reports" / "native_regression"),
        help="Directory that will receive suite summaries and the native regression manifest",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = run_native_regression(output_root=args.output_root)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"native regression: {manifest['status']} -> {Path(args.output_root).resolve() / 'release_manifest.json'}")


if __name__ == "__main__":
    main()
