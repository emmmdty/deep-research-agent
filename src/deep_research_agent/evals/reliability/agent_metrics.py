"""Deterministic per-dimension metrics for the model-driven agent runtime.

Zero provider tokens, zero network. One scripted research job (model fake +
governed tool gateway) is measured along the dimensions an interviewer (or a
production SRE) cares about:

- **Retrieval**: sources gathered, deduplication, full-page reads, and the
  grounding acceptance rate — how many model-submitted claims survive the
  verbatim-evidence gate.
- **Reasoning**: reflection rounds, gap-triggered follow-up rate, and the
  coverage decisions the model makes.
- **Context management**: prompt size per agent stage (planning / reflection /
  page selection / extraction), growth across rounds, and estimated tokens.
- **Cache hit rate**: a governed tool cache (TTL) measured across two runs of
  the same job — steady-state hit rate on repeated work.
- **Memory**: subject-scoped recall/precision of the memory service, plus
  tenant isolation.
- **Token usage**: estimated tokens per stage and per grounded claim.
"""

from __future__ import annotations

import time
from typing import Any

from deep_research_agent.evals.reliability.fault_injection import (
    _claim_entry,
    _snippet,
    _snippet_text,
    ScriptedChat,
    build_scripted_gateway,
)
from deep_research_agent.kernel.contracts import ResearchBrief, TaskSpec
from deep_research_agent.memory_v2.models import Sensitivity
from deep_research_agent.memory_v2.service import MemoryService
from deep_research_agent.orchestration.dag import ResearchDAG
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
from deep_research_agent.orchestration.workers import TaskExecutionContext, WorkerOutput
from deep_research_agent.domain_packs.models import DomainPack

_JOB_ID = "agent-metrics"
_OBJECTIVE = "What are the travel rules and prices for high-speed rail student tickets in 2026?"
_TOKENS_PER_CHAR = 0.25
_INPUT_TOKEN_PRICE_PER_M = 0.30
_OUTPUT_TOKEN_PRICE_PER_M = 1.20
# Model output per call in this scripted run: prompt-path JSON + tool decisions
# are small; estimate output at 20% of input size to keep the estimate honest.
_OUTPUT_RATIO = 0.2

_DOMAIN_PACK = DomainPack(
    schema_version="1.0",
    pack_id="company-trusted",
    version="1.0.0",
    title="Company Trusted",
    description="agent metrics fixture",
    entity_types=["company", "product"],
    relations=[],
    research_questions=["What changed?"],
    source_types=["web"],
)


def _brief() -> ResearchBrief:
    return ResearchBrief(
        brief_id="agent-metrics-brief",
        job_id=_JOB_ID,
        question=_OBJECTIVE,
        domain_pack_id="company-trusted",
    )


def _multi_hop_script() -> list[dict[str, Any]]:
    """A realistic scripted model: two rounds, one gap-triggered follow-up.

    Mirrors the real control flow: round 2 never runs a second coverage
    assessment (the round budget is exhausted), so the script has exactly one
    coverage entry and one plan entry per round.
    """

    return [
        {
            "plan_queries": {
                "queries": [
                    {"query": "高铁学生票 购票规则 2026", "tool": "web_search"},
                    {"query": "学生票 折扣比例 铁路局", "tool": "web_search"},
                ]
            }
        },
        {"assess_coverage": {"covered": False, "gaps": ["换乘优惠与退改签规则"]}},
        {
            "plan_queries": {
                "queries": [
                    {"query": "高铁学生票 换乘 退改签 2026", "tool": "web_search"},
                ]
            }
        },
        {
            "select_pages": {
                # select_pages may only return URLs already gathered as sources
                # (the gateway governance contract), so pick a source URL
                "urls": ["https://example.com/1"],
            }
        },
        {
            "submit_claims": {
                "claims": [
                    _claim_entry("学生票享受公布票价五折优惠。", 1, "学生票享受公布票价五折优惠"),
                    _claim_entry("每学年可购买四次家庭与学校间单程票。", 1, "每学年可购买四次家庭与学校间单程票"),
                    _claim_entry("预售期与学生票验证与普通票一致。", 2, "预售期与学生票验证与普通票一致"),
                    # deliberately attributed to the wrong source: the verbatim
                    # gate must reject it (grounding acceptance probe)
                    _claim_entry("退票需在发车前 48 小时办理。", 1, "退票需在发车前 48 小时办理"),
                    _claim_entry("学生票不可用于任意区间。", 3, "学生票不可用于任意区间"),
                ]
            }
        },
    ]


def _metric_sources() -> list[dict[str, Any]]:
    return [
        _snippet(1, "铁路12306 规定学生票享受公布票价五折优惠，每学年可购买四次家庭与学校间单程票。"),
        _snippet(2, "12306 公告：学生票预售期与学生票验证与普通票一致。"),
        _snippet(3, "票务平台提示：学生票不可用于任意区间，退票需在发车前 48 小时办理。"),
    ]


def _metric_gateway(cache_ttl_seconds: float = 0.0):
    return build_scripted_gateway(
        responses={
            "web_search": _metric_sources(),
            "fetch_page": {
                "url": "https://www.12306.cn/student-ticket-rules",
                "final_url": "https://www.12306.cn/student-ticket-rules",
                "title": "学生票规则",
                "content": _snippet_text() * 2,
            },
        },
        cache_ttl_seconds=cache_ttl_seconds,
    )


async def _run_metrics_job(chat: ScriptedChat, gateway) -> dict[str, Any]:
    dag = ResearchDAG(
        job_id=_JOB_ID,
        tasks=[
            TaskSpec(
                task_id="research-01-student-tickets",
                job_id=_JOB_ID,
                kind="research",
                role="researcher",
                objective=_OBJECTIVE,
                depends_on=[],
                input_artifacts=[],
                output_schema={"type": "object"},
                budget={"max_tool_calls": 16},
                idempotency_key=f"{_JOB_ID}:research-01-student-tickets",
            ),
            TaskSpec(
                task_id="critic",
                job_id=_JOB_ID,
                kind="critic",
                role="critic",
                objective="Synthesize the report.",
                depends_on=["research-01-student-tickets"],
                input_artifacts=[],
                output_schema={"type": "object"},
                budget={},
                idempotency_key=f"{_JOB_ID}:critic",
            ),
        ],
    )

    class RoleWorker:
        async def execute(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput:
            if task.role == "researcher":
                from deep_research_agent.agents.researcher import LLMResearcherWorker
                return await LLMResearcherWorker(chat=chat).execute(task, context)
            if task.role == "critic":
                from deep_research_agent.agents.critic import LLMCriticWorker
                return await LLMCriticWorker(chat=chat).execute(task, context)
            raise RuntimeError(f"no worker for role {task.role!r}")

    scheduler = ResearchScheduler(worker=RoleWorker(), max_workers=4, tool_gateway=gateway)
    result = await scheduler.run(
        SchedulerJob(job_id=_JOB_ID, tenant_id="default"),
        dag,
        {"version_id": "agent-metrics-v1"},
    )
    researcher_out = next(
        (out for out in result.task_outputs.values() if "agentic" in out), {}
    )
    critic_out = next(
        (out for out in result.task_outputs.values() if "deterministic_review" in out), {}
    )
    packets = [
        packet
        for task_result in result.task_results.values()
        for packet in task_result.evidence_packets
    ]
    claims = [claim for packet in packets for claim in packet.claims]
    return {
        "status": result.status,
        "researcher": researcher_out,
        "critic": critic_out,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "chat": chat,
    }


def _estimate_tokens(prompt_sizes: list[dict[str, int]]) -> dict[str, Any]:
    stages: dict[str, dict[str, int]] = {}
    for entry in prompt_sizes:
        bucket = stages.setdefault(entry["stage"], {"system_chars": 0, "user_chars": 0, "calls": 0})
        bucket["system_chars"] += entry["system_chars"]
        bucket["user_chars"] += entry["user_chars"]
        bucket["calls"] += 1
    total_input_tokens = 0
    rows: list[dict[str, Any]] = []
    for stage in ("tool_loop", "chat_json", "chat"):
        if stage not in stages:
            continue
        bucket = stages[stage]
        input_tokens = round(
            (bucket["system_chars"] + bucket["user_chars"]) * _TOKENS_PER_CHAR
        )
        total_input_tokens += input_tokens
        rows.append(
            {
                "stage": stage,
                "calls": bucket["calls"],
                "system_chars": bucket["system_chars"],
                "user_chars": bucket["user_chars"],
                "est_input_tokens": input_tokens,
            }
        )
    output_tokens = round(total_input_tokens * _OUTPUT_RATIO)
    cost = (
        total_input_tokens / 1_000_000 * _INPUT_TOKEN_PRICE_PER_M
        + output_tokens / 1_000_000 * _OUTPUT_TOKEN_PRICE_PER_M
    )
    return {
        "per_stage": rows,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": output_tokens,
        "est_cost_usd": round(cost, 4),
    }


def _retrieval_metrics(claims: list[dict[str, Any]], researcher: dict[str, Any]) -> dict[str, Any]:
    submitted = 5
    accepted = len(claims)
    return {
        "queries_issued": researcher.get("query_count", 0),
        "sources_gathered": researcher.get("source_count", 0),
        "full_page_reads": researcher.get("page_count", 0),
        "submitted_claims": submitted,
        "accepted_claims": accepted,
        "grounding_acceptance_rate": round(accepted / submitted, 3),
        "claims_per_source": round(accepted / max(researcher.get("source_count", 1), 1), 3),
    }


def _reasoning_metrics(researcher: dict[str, Any]) -> dict[str, Any]:
    assessments = researcher.get("coverage_assessments", [])
    gaps = [
        str(gap)
        for assessment in assessments
        for gap in assessment.get("gaps", [])
        if str(gap).strip()
    ]
    return {
        "rounds_used": researcher.get("rounds", 0),
        "coverage_assessments": len(assessments),
        "model_assessed_covered": sum(1 for a in assessments if a.get("covered")),
        "gap_triggers": len(gaps),
        "follow_up_round_rate": round(min(len(gaps), 1), 2),
    }


async def _cache_metrics() -> dict[str, Any]:
    gateway = _metric_gateway(cache_ttl_seconds=3600.0)
    first = await _run_metrics_job(
        ScriptedChat(tool_loop_script=_multi_hop_script(), text_script=["report"]),
        gateway,
    )
    second = await _run_metrics_job(
        ScriptedChat(tool_loop_script=_multi_hop_script(), text_script=["report"]),
        gateway,
    )
    # Count cache hits by re-invoking the same tool arguments through the gateway
    # (same job id, same role, same arguments → same cache key).
    from deep_research_agent.tool_gateway.models import ToolExecutionContext, ToolInvocation

    task = TaskSpec(
        task_id="research-01-student-tickets",
        job_id=_JOB_ID,
        kind="research",
        role="researcher",
        objective=_OBJECTIVE,
        depends_on=[],
        input_artifacts=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 16},
        idempotency_key=f"{_JOB_ID}:research-01-student-tickets",
    )
    invocations = [
        ToolInvocation(
            invocation_id="inv-1",
            tool_name="web_search",
            tenant_id="default",
            idempotency_key="metrics-1",
            arguments={"query": "高铁学生票 购票规则 2026", "max_results": 4},
        ),
        ToolInvocation(
            invocation_id="inv-2",
            tool_name="web_search",
            tenant_id="default",
            idempotency_key="metrics-2",
            arguments={"query": "学生票 折扣比例 铁路局", "max_results": 4},
        ),
    ]
    context = ToolExecutionContext(tenant_id="default", role="researcher", job_id=_JOB_ID)
    hits = 0
    for invocation in invocations:
        for _ in range(2):
            envelope = gateway.invoke(task, invocation, context)
            if envelope.from_cache:
                hits += 1
    total = len(invocations) * 2
    return {
        "cache_ttl_seconds": 3600,
        "probes": total,
        "cache_hits": hits,
        "cache_hit_rate": round(hits / total, 3),
        "job_status_first_run": first["status"],
        "job_status_second_run": second["status"],
    }


def _memory_metrics() -> dict[str, Any]:
    service = MemoryService()
    facts = [
        ("seat_preference", "prefers window seats on high-speed rail"),
        ("booking_lead_time", "usually books 7 days ahead"),
        ("employer", "works at a software company in Hangzhou"),
        ("home", "lives in Dongguan"),
        ("route", "commutes Hangzhou-Dongguan monthly"),
        ("discount", "holds a student discount for the summer"),
        ("contact", "prefers WeChat for booking confirmations"),
        ("meal", "avoids airline meals"),
        ("loyalty", "collects rail loyalty points"),
        ("budget", "targets trips under 400 yuan"),
    ]
    for index, (key, content) in enumerate(facts):
        service.write(
            tenant_id="tenant-a",
            subject_id="user-42",
            scope="user_memory",
            key=key,
            content=content,
            provenance={"source": "metrics-fixture", "index": index},
            sensitivity=Sensitivity.INTERNAL,
        )
    relevant_queries = [
        "window seats high-speed rail",
        "books 7 days ahead",
        "software company Hangzhou",
        "Dongguan",
        "Hangzhou Dongguan monthly",
        "student discount summer",
    ]
    noise_queries = [
        "stock market",
        "quantum computing",
        "baking recipes",
        "soccer scores",
    ]
    hits = sum(
        len(service.search(query, tenant_id="tenant-a", scope="user_memory")) > 0
        for query in relevant_queries
    )
    precision = 0.0
    checked = 0
    for query in noise_queries:
        matches = service.search(query, tenant_id="tenant-a", scope="user_memory")
        checked += 1
        if not matches:
            precision += 1
    isolated = False
    try:
        service.search("window seats", tenant_id="tenant-b", scope="user_memory")
    except PermissionError:
        isolated = True
    return {
        "stored_facts": len(facts),
        "recall_at_top": round(hits / len(relevant_queries), 3),
        "noise_precision": round(precision / checked, 3),
        "tenant_isolation_enforced": isolated,
    }


async def run_metrics() -> dict[str, Any]:
    chat = ScriptedChat(
        tool_loop_script=_multi_hop_script(),
        text_script=["## Executive Summary\n- 学生票五折。\n"],
    )
    gateway = _metric_gateway()
    started = time.perf_counter()
    job = await _run_metrics_job(chat, gateway)
    wall_ms = int((time.perf_counter() - started) * 1000)
    tokens = _estimate_tokens(chat.prompt_sizes)
    return {
        "job": {
            "status": job["status"],
            "wall_ms": wall_ms,
            "report_markdown": job["critic"].get("report_markdown", ""),
        },
        "retrieval": _retrieval_metrics(job["claims"], job["researcher"]),
        "reasoning": _reasoning_metrics(job["researcher"]),
        "context": {"prompt_metrics": tokens},
        "cache": await _cache_metrics(),
        "memory": _memory_metrics(),
    }


def format_report(payload: dict[str, Any]) -> str:
    retrieval = payload["retrieval"]
    reasoning = payload["reasoning"]
    tokens = payload["context"]["prompt_metrics"]
    cache = payload["cache"]
    memory = payload["memory"]
    job = payload["job"]
    stage_rows = "\n".join(
        f"| {row['stage']} | {row['calls']} | {row['system_chars']} | {row['user_chars']} "
        f"| {row['est_input_tokens']} |"
        for row in tokens["per_stage"]
    )
    return "\n".join(
        [
            "# Agent Dimension Metrics (deterministic)",
            "",
            "One scripted research job (model fake + governed tool gateway) measured along the dimensions that production review cares about. Zero provider tokens, zero network.",
            "",
            f"Job status: **{job['status']}** · wall time: {job['wall_ms']} ms · report emitted: {bool(job['report_markdown'])}",
            "",
            "## Retrieval",
            "",
            f"- Queries issued: **{retrieval['queries_issued']}**",
            f"- Unique sources gathered: **{retrieval['sources_gathered']}**",
            f"- Full-page reads: **{retrieval['full_page_reads']}**",
            f"- Grounding acceptance rate (model-submitted → verbatim-grounded): **{retrieval['grounding_acceptance_rate']:.0%}** ({retrieval['accepted_claims']}/{retrieval['submitted_claims']})",
            f"- Grounded claims per source: **{retrieval['claims_per_source']}**",
            "",
            "## Reasoning",
            "",
            f"- Reflection rounds used: **{reasoning['rounds_used']}**",
            f"- Coverage assessments: **{reasoning['coverage_assessments']}** · model said covered: {reasoning['model_assessed_covered']}",
            f"- Gap-triggered follow-up rounds: **{reasoning['gap_triggers']}**",
            "",
            "## Context Management",
            "",
            "| Stage | Calls | System chars | User chars | Est. input tokens |",
            "| --- | ---: | ---: | ---: | ---: |",
            stage_rows,
            f"- Total est. input tokens: **{tokens['total_input_tokens']}** · output: {tokens['total_output_tokens']}",
            f"- Est. cost at ${_INPUT_TOKEN_PRICE_PER_M}/M in + ${_OUTPUT_TOKEN_PRICE_PER_M}/M out: **${tokens['est_cost_usd']}**",
            "",
            "## Tool Cache",
            "",
            f"- TTL: {cache['cache_ttl_seconds']}s · probes: {cache['probes']} · hits: {cache['cache_hits']}",
            f"- Steady-state cache hit rate on repeated work: **{cache['cache_hit_rate']:.0%}**",
            f"- Job status (first / second run): {cache['job_status_first_run']} / {cache['job_status_second_run']}",
            "",
            "## Memory",
            "",
            f"- Subject-scoped recall@1: **{memory['recall_at_top']:.0%}** ({memory['stored_facts']} stored facts, 6 relevant queries)",
            f"- Noise precision (irrelevant queries must not match): **{memory['noise_precision']:.0%}**",
            f"- Cross-tenant access denied: **{memory['tenant_isolation_enforced']}**",
            "",
        ]
    )
