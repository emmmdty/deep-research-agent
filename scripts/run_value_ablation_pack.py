"""Generate the Phase 08 ablation and performance pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.value_ablations import build_value_ablation_pack


def run_value_ablation_pack(
    *,
    baseline_root: str | Path,
    followup_root: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    return build_value_ablation_pack(
        baseline_root=baseline_root,
        followup_root=followup_root,
        output_root=output_root,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the follow-up ablation and performance pack")
    parser.add_argument(
        "--baseline-root",
        default=str(Path("evals") / "reports" / "phase5_local_smoke"),
        help="Committed Phase 5 smoke root",
    )
    parser.add_argument(
        "--followup-root",
        default=str(Path("evals") / "reports" / "followup_metrics"),
        help="Phase 7 follow-up metrics root",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path("evals") / "reports" / "followup_metrics"),
        help="Directory for ablation/performance artifacts",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_value_ablation_pack(
        baseline_root=args.baseline_root,
        followup_root=args.followup_root,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ablation pack -> {Path(result['artifacts']['ablation_summary_csv']).resolve()}")


if __name__ == "__main__":
    main()
