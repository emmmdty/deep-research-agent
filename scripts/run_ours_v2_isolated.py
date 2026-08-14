"""Canonical scheduler-v2 agent isolated runner for the comparator suite.

Runs the model-driven evidence-first agent (LLM planner -> bounded DAG
scheduler -> governed web/GitHub/arXiv search -> critic synthesis -> report
bundle) on one topic, exactly the same runtime path as the product API
``create_run``, and writes the report plus metadata so the head-to-head
comparator suite can judge it against external frameworks.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production \\
        uv run python scripts/run_ours_v2_isolated.py \\
            --topic "..." --report-path out.md --meta-path meta.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.settings import get_settings  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from deep_research_agent.agents.factory import MultiRoleWorker, build_gateway  # noqa: E402
from deep_research_agent.agents.planner import LLMResearchPlanner  # noqa: E402
from deep_research_agent.agents.critic import LLMCriticWorker  # noqa: E402
from deep_research_agent.agents.researcher import LLMResearcherWorker  # noqa: E402
from deep_research_agent.domain_packs.registry import DomainPackRegistry  # noqa: E402
from deep_research_agent.kernel.contracts import ResearchBrief  # noqa: E402
from deep_research_agent.observability.cost_tracker import get_tracker  # noqa: E402
from deep_research_agent.orchestration.scheduler import (  # noqa: E402
    ResearchScheduler,
    SchedulerJob,
)
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2  # noqa: E402

CONSTRAINTS = {
    "must_cover": ["overview", "analysis", "comparison", "references"],
    "answer_in_chinese": True,
    "focus": "2026 年可验证的现状与事实，优先官方来源",
}


def _job_id() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


async def _run(topic: str) -> tuple[str, dict]:
    settings = get_settings()
    if not settings.llm_api_key or not settings.tavily_api_key:
        raise SystemExit("LLM and TAVILY credentials are required")

    job_id = _job_id()
    brief = ResearchBrief(
        brief_id=f"brief-{job_id}",
        job_id=job_id,
        question=topic,
        constraints=CONSTRAINTS,
        domain_pack_id="event-graph-agents-llms",
    )
    domain_pack = DomainPackRegistry().load(brief.domain_pack_id)
    planner = LLMResearchPlanner(max_objectives=4)
    dag = planner.plan(brief, domain_pack)

    gateway = build_gateway()
    worker = MultiRoleWorker(researcher=LLMResearcherWorker(), critic=LLMCriticWorker())
    scheduler = ResearchScheduler(worker=worker, tool_gateway=gateway, max_workers=4, max_attempts=2)
    result = await scheduler.run(
        SchedulerJob(job_id=job_id, tenant_id="comparator"),
        dag,
        {"model": "scheduler-v2-live", "comparator": "ours_v2"},
    )

    critic_output = result.task_outputs.get("critic", {})
    report = str(critic_output.get("report_markdown") or "")
    if not report.strip():
        raise RuntimeError(f"scheduler-v2 job {job_id} produced no report")

    sources = [
        artifact
        for task_result in result.task_results.values()
        for packet in task_result.evidence_packets
        for artifact in packet.artifacts
    ]
    claims = [
        claim
        for task_result in result.task_results.values()
        for packet in task_result.evidence_packets
        for claim in packet.claims
    ]
    tracker = get_tracker().metrics
    meta = {
        "comparator": "ours_v2",
        "topic": topic,
        "model": settings.llm_model_name,
        "job_id": job_id,
        "status": result.status,
        "claims": len(claims),
        "sources": len(sources),
        "queries": [
            str(q.get("query", ""))
            for task_output in result.task_outputs.values()
            for q in task_output.get("queries", [])
        ],
        "injection_stats": {
            task_id: task_output.get("injection_stats", {})
            for task_id, task_output in result.task_outputs.items()
        },
        "cost": tracker.to_dict(),
    }
    return report, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the canonical scheduler-v2 agent")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--report-path", required=True, type=Path)
    parser.add_argument("--meta-path", required=True, type=Path)
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    started = time.monotonic()
    report, meta = asyncio.run(_run(args.topic))
    meta["wall_seconds"] = round(time.monotonic() - started, 2)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    args.meta_path.parent.mkdir(parents=True, exist_ok=True)
    args.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ours_v2: report written to {args.report_path} ({meta['wall_seconds']}s)")


if __name__ == "__main__":
    main()
