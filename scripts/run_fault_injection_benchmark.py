"""Run the deterministic fault-injection fallback benchmark and write its report.

Deterministic (zero provider tokens, zero network). Outputs:
``evals/reports/fault_injection/REPORT.md`` and ``summary.json``.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from deep_research_agent.evals.reliability.fault_injection import (
    format_report,
    run_all,
)

_OUTPUT_ROOT = Path("evals") / "reports" / "fault_injection"


def main() -> None:
    logger.info("running fault-injection fallback benchmark (deterministic)")
    payload = asyncio.run(run_all(_OUTPUT_ROOT))
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (_OUTPUT_ROOT / "REPORT.md").write_text(format_report(payload), encoding="utf-8")
    (_OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"fault-injection benchmark written to {_OUTPUT_ROOT}/")


if __name__ == "__main__":
    main()
