"""Live demo driver for the canonical scheduler-v2 model-driven agent.

Runs a full evidence-first research job in-process against live providers
(LLM + governed web/GitHub/arXiv search + full-page reading), then compiles
the audit-ready report bundle. This is the same runtime path as the product
API ``create_run`` (``runtime_path="scheduler-v2"``), driven directly so a
demo needs no database or web server.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production AGENT_PLANNER_ENABLED=true \\
        uv run python scripts/run_route_demo.py

The demo topic is a high-accuracy routing question (Hangzhou -> Dongguan)
with explicit personas (high-speed rail, flight incl. Loong Air flight pass,
student ticket discount); pass ``--topic`` / ``--objectives`` to change it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from loguru import logger

from configs.settings import get_settings
from deep_research_agent.agents.critic import LLMCriticWorker
from deep_research_agent.agents.factory import MultiRoleWorker, build_gateway
from deep_research_agent.agents.planner import LLMResearchPlanner
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.domain_packs.registry import DomainPackRegistry
from deep_research_agent.kernel.contracts import CorpusManifest, ResearchBrief, ResearchGraph
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEMO_OBJECTIVES = [
    "杭州到东莞的高铁出行方案：直达或中转车次、耗时与票价",
    "杭州到东莞的飞机出行方案：航班选择、是否需经深圳或广州中转、总耗时与费用",
    "长龙航空畅飞卡的使用规则与可用航线，能否用于杭州往返广州或深圳",
    "高铁学生票（学生证）的现行购票规则、折扣比例与购票条件",
]

DEMO_CONSTRAINTS = {
    "must_cover": ["high_speed_rail", "flight", "bus_or_transfer", "student_ticket"],
    "answer_in_chinese": True,
    "focus": "2026 年现行可执行的真实方案，优先官方来源（12306、航司官网、铁路12306）",
}


def _job_id() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


async def _run(
    topic: str,
    objectives: list[str],
    *,
    out_dir: Path,
) -> None:
    settings = get_settings()
    if not settings.llm_api_key:
        raise SystemExit("LLM credentials are required: set LLM_API_KEY / LLM_BASE_URL in .env")
    if not settings.tavily_api_key:
        raise SystemExit("TAVILY_API_KEY is required for web search in this demo")

    job_id = _job_id()
    job_dir = out_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    brief = ResearchBrief(
        brief_id=f"brief-{job_id}",
        job_id=job_id,
        question=topic,
        objectives=objectives,
        constraints=DEMO_CONSTRAINTS,
        domain_pack_id="event-graph-agents-llms",
    )
    domain_pack = DomainPackRegistry().load(brief.domain_pack_id)
    planner = LLMResearchPlanner(max_objectives=4)
    dag = planner.plan(brief, domain_pack, require_objectives=objectives)

    gateway = build_gateway()
    worker = MultiRoleWorker(
        researcher=LLMResearcherWorker(),
        critic=LLMCriticWorker(),
    )
    scheduler = ResearchScheduler(
        worker=worker,
        tool_gateway=gateway,
        max_workers=4,
        max_attempts=2,
    )

    logger.info("=== demo run {} ===", job_id)
    logger.info("planner produced {} tasks: {}", len(dag.tasks), [t.task_id for t in dag.tasks])
    result = await scheduler.run(
        SchedulerJob(job_id=job_id, tenant_id="default"),
        dag,
        {"model": planner.__class__.__name__, "runtime": "scheduler-v2", "demo": True},
    )

    sources: list = []
    claims: list = []
    packets: list = []
    for task_result in result.task_results.values():
        for packet in task_result.evidence_packets:
            packets.append(packet)
            claims.extend(packet.claims)
            sources.extend(packet.artifacts)

    critic_output = result.task_outputs.get("critic", {})
    report_markdown = str(critic_output.get("report_markdown") or "")
    graph_payload = critic_output.get("research_graph") or {"nodes": [], "edges": []}
    if isinstance(graph_payload, dict):
        research_graph = ResearchGraph.model_validate(graph_payload)
    else:
        research_graph = graph_payload

    corpus_manifest = CorpusManifest(
        manifest_id=f"corpus:{job_id}",
        document_version_ids=tuple(
            sorted(
                {
                    artifact.metadata.get("document_version_id")
                    for artifact in sources
                    if artifact.metadata.get("document_version_id")
                }
            )
        ),
        content_hashes={
            artifact.metadata.get("document_version_id"): artifact.content_sha256
            for artifact in sources
            if artifact.metadata.get("document_version_id")
        },
        critical_claims_allowed={
            artifact.metadata.get("document_version_id"): True
            for artifact in sources
            if artifact.metadata.get("document_version_id")
        },
    )
    compiler = ReportBundleCompilerV2()
    bundle = compiler.compile(
        report_markdown=report_markdown,
        claims=claims,
        evidence_packets=packets,
        critic_decisions=result.critic_decisions,
        research_graph=research_graph,
        sources=sources,
        corpus_manifest=corpus_manifest,
        run_manifest={"job_id": job_id, "status": result.status},
    )

    (job_dir / "report_bundle.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    (job_dir / "report.md").write_text(report_markdown, encoding="utf-8")
    (job_dir / "scheduler_checkpoints.json").write_text(
        json.dumps(
            [c.model_dump(mode="json") for c in result.checkpoints], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (job_dir / "run_summary.json").write_text(
        json.dumps(_run_summary(result, sources), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\njob: {job_id} | status: {result.status}")
    print(f"tasks: {len(result.task_results)} | claims: {len(claims)} | sources: {len(sources)}")
    print(f"report: {job_dir / 'report.md'}")
    print(f"bundle: {job_dir / 'report_bundle.json'}")
    if report_markdown:
        print("\n--- report preview ---\n")
        print(report_markdown[:3000])


def _run_summary(result, sources) -> dict:
    from collections import Counter

    queries: list[str] = []
    pages: list[str] = []
    coverage: list = []
    fallbacks = 0
    for task_output in result.task_outputs.values():
        queries.extend(str(q.get("query", "")) for q in task_output.get("queries", []))
        pages.extend(str(p) for p in task_output.get("page_urls", []))
        coverage.extend(task_output.get("coverage_assessments", []))
        fallbacks += int(task_output.get("extraction_fallbacks", 0) or 0)
    return {
        "job_id": result.job_id,
        "status": result.status,
        "tasks": sorted(result.task_results),
        "attempts": result.attempts,
        "queries": queries,
        "full_page_reads": pages,
        "coverage_assessments": coverage,
        "extraction_fallbacks": fallbacks,
        "source_count": len(sources),
        "source_kinds": dict(
            Counter(str(s.metadata.get("source_kind", "snippet")) for s in sources)
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the scheduler-v2 live demo job")
    parser.add_argument("--topic", default="从杭州到东莞的出行路线方案对比")
    parser.add_argument(
        "--objectives",
        nargs="*",
        default=DEMO_OBJECTIVES,
        help="research sub-objectives passed to the planner (default: demo personas)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "workspace" / "research_jobs",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | <cyan>{message}</cyan>",
        level="INFO",
    )
    asyncio.run(_run(args.topic, list(args.objectives), out_dir=args.out_dir))


if __name__ == "__main__":
    main()
