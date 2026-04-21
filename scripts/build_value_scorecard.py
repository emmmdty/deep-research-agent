"""Render the Phase 09 reviewer-facing value scorecard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_research_agent.evals.value_scorecard import build_value_scorecard


def run_value_scorecard(
    *,
    release_manifest_path: str | Path,
    metrics_root: str | Path,
    docs_root: str | Path,
    metrics_readme_path: str | Path,
) -> dict[str, Any]:
    return build_value_scorecard(
        release_manifest_path=release_manifest_path,
        metrics_root=metrics_root,
        docs_root=docs_root,
        metrics_readme_path=metrics_readme_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Phase 09 public value scorecard")
    parser.add_argument(
        "--release-manifest",
        default=str(Path("evals") / "reports" / "phase5_local_smoke" / "release_manifest.json"),
        help="Committed release manifest path",
    )
    parser.add_argument(
        "--metrics-root",
        default=str(Path("evals") / "reports" / "followup_metrics"),
        help="Follow-up metrics artifact root",
    )
    parser.add_argument(
        "--docs-root",
        default=str(Path("docs") / "final"),
        help="Directory that will receive VALUE_SCORECARD.md and VALUE_SCORECARD.json",
    )
    parser.add_argument(
        "--metrics-readme",
        default=str(Path("evals") / "reports" / "followup_metrics" / "README.md"),
        help="Path to the follow-up metrics README",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_value_scorecard(
        release_manifest_path=args.release_manifest,
        metrics_root=args.metrics_root,
        docs_root=args.docs_root,
        metrics_readme_path=args.metrics_readme,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"value scorecard -> {Path(result['artifacts']['scorecard_markdown']).resolve()}")


if __name__ == "__main__":
    main()
