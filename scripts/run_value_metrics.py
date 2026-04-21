"""Render the Phase 07 follow-up value metrics pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.value_metrics import build_value_metrics_pack


def run_value_metrics_pack(*, source_roots: list[str | Path], output_root: str | Path) -> dict[str, Any]:
    return build_value_metrics_pack(source_roots=source_roots, output_root=output_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate follow-up value metrics from eval artifacts")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        help="Release root (contains release_manifest.json) or suite root (contains summary.json). Repeatable.",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path("evals") / "reports" / "followup_metrics"),
        help="Directory for generated value metrics artifacts",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source_roots = args.source_root or [str(Path("evals") / "reports" / "phase5_local_smoke")]
    result = run_value_metrics_pack(source_roots=source_roots, output_root=args.output_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"value metrics -> {Path(result['artifacts']['headline_metrics']).resolve()}")


if __name__ == "__main__":
    main()
