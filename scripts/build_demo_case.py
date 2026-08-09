"""Deterministically generate a high-quality demo research case for the demo site.

The demo case mirrors the exact report_bundle.json / trace.jsonl contracts of a real
scheduler-v2 run, but its content is authored demo material based on public 2025
information. It exists so reviewers can experience the full product flow (planning ->
parallel research -> audit -> report) without API keys or network access.

The bundle carries an explicit `demo_notice` and `job.status="demo"` so it can never be
confused with a live research result.

Usage:
    uv run python scripts/build_demo_case.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "evals" / "fixtures" / "runs" / "demo-anthropic"

JOB_ID = "demo-anthropic-20260809"
PROMPT = (
    "研究 Anthropic 公司：核心产品（Claude 模型家族、Claude Code、MCP 协议）、"
    "商业模式与融资历程、多 agent 研发实践及其行业影响。"
)

SOURCES = [
    {
        "source_id": "source-1",
        "citation_id": 1,
        "source_type": "web",
        "title": "Anthropic — About (official company page)",
        "canonical_uri": "https://www.anthropic.com/about",
        "query": "Anthropic company founded Dario Amodei OpenAI",
        "selected": True,
        "snapshot_ref": "snapshot-0001",
        "metadata": {"auth_required": False, "fetched_at": "2026-08-09T00:00:00Z"},
    },
    {
        "source_id": "source-2",
        "citation_id": 2,
        "source_type": "web",
        "title": "Anthropic — Announcing our $3.5B Series E (2025-03)",
        "canonical_uri": "https://www.anthropic.com/news/series-e",
        "query": "Anthropic Series E $3.5 billion valuation 61.5 billion",
        "selected": True,
        "snapshot_ref": "snapshot-0002",
        "metadata": {"auth_required": False},
    },
    {
        "source_id": "source-3",
        "citation_id": 3,
        "source_type": "web",
        "title": "Anthropic — Introducing Claude Code (2025-02)",
        "canonical_uri": "https://www.anthropic.com/news/claude-code",
        "query": "Claude Code CLI coding agent launch",
        "selected": True,
        "snapshot_ref": "snapshot-0003",
        "metadata": {"auth_required": False},
    },
    {
        "source_id": "source-4",
        "citation_id": 4,
        "source_type": "web",
        "title": "Anthropic — Model Context Protocol announcement (2024-11)",
        "canonical_uri": "https://www.anthropic.com/news/model-context-protocol",
        "query": "Model Context Protocol open standard tool interoperability",
        "selected": True,
        "snapshot_ref": "snapshot-0004",
        "metadata": {"auth_required": False},
    },
    {
        "source_id": "source-5",
        "citation_id": 5,
        "source_type": "web",
        "title": "Anthropic — How we built our multi-agent research system (2025-06)",
        "canonical_uri": "https://www.anthropic.com/engineering/built-multi-agent-research-system",
        "query": "Anthropic multi-agent research system orchestrator workers 90 percent",
        "selected": True,
        "snapshot_ref": "snapshot-0005",
        "metadata": {"auth_required": False},
    },
    {
        "source_id": "source-6",
        "citation_id": 6,
        "source_type": "web",
        "title": "Amazon — Amazon invests additional $4B in Anthropic (2024-11)",
        "canonical_uri": "https://www.aboutamazon.com/news/company-news/amazon-anthropic-4-billion-investment",
        "query": "Amazon Anthropic 4 billion investment Bedrock",
        "selected": True,
        "snapshot_ref": "snapshot-0006",
        "metadata": {"auth_required": False},
    },
    {
        "source_id": "source-7",
        "citation_id": 7,
        "source_type": "web",
        "title": "Reuters — Anthropic in talks to raise at $300 billion valuation (2025-09)",
        "canonical_uri": "https://www.reuters.com/technology/artificial-intelligence/anthropic-talks-raise-300-billion-valuation-2025-09-16/",
        "query": "Anthropic funding round valuation 300 billion Reuters",
        "selected": True,
        "snapshot_ref": "snapshot-0007",
        "metadata": {"auth_required": True},
    },
    {
        "source_id": "source-8",
        "citation_id": 8,
        "source_type": "web",
        "title": "The Information — Anthropic approaches $30 billion annualized revenue run rate (2025-09)",
        "canonical_uri": "https://www.theinformation.com/articles/anthropic-approaches-30-billion-annualized-revenue",
        "query": "Anthropic annualized revenue run rate 30 billion",
        "selected": True,
        "snapshot_ref": "snapshot-0008",
        "metadata": {"auth_required": True},
    },
]

EVIDENCE = [
    {
        "evidence_id": "evidence-1",
        "snapshot_id": "snapshot-0001",
        "source_id": "source-1",
        "locator": {"kind": "snippet", "citation_id": 1},
        "excerpt": "Anthropic is an AI safety and research company founded in 2021 by Dario Amodei and Daniela Amodei, with core members coming from OpenAI.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-2",
        "snapshot_id": "snapshot-0002",
        "source_id": "source-2",
        "locator": {"kind": "snippet", "citation_id": 2},
        "excerpt": "We are announcing a $3.5B Series E round, which values the company at $61.5 billion post-money.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-3",
        "snapshot_id": "snapshot-0003",
        "source_id": "source-3",
        "locator": {"kind": "snippet", "citation_id": 3},
        "excerpt": "Claude Code is our agentic coding tool, available today in research preview, that operates directly in a terminal.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-4",
        "snapshot_id": "snapshot-0004",
        "source_id": "source-4",
        "locator": {"kind": "snippet", "citation_id": 4},
        "excerpt": "Today we are open-sourcing the Model Context Protocol, an open standard that connects AI assistants to data and tools.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-5",
        "snapshot_id": "snapshot-0005",
        "source_id": "source-5",
        "locator": {"kind": "snippet", "citation_id": 5},
        "excerpt": "The multi-agent system scored 90.2% higher than a single Opus 4 agent on our internal research evaluation.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-6",
        "snapshot_id": "snapshot-0006",
        "source_id": "source-6",
        "locator": {"kind": "snippet", "citation_id": 6},
        "excerpt": "Amazon has invested an additional $4 billion in Anthropic, bringing Amazon's total investment to $8 billion.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-7",
        "snapshot_id": "snapshot-0005",
        "source_id": "source-5",
        "locator": {"kind": "snippet", "citation_id": 5},
        "excerpt": "Lead agent delegates research topics to parallel sub-agents; sub-agents write findings to the filesystem to avoid context loss.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-8",
        "snapshot_id": "snapshot-0007",
        "source_id": "source-7",
        "locator": {"kind": "snippet", "citation_id": 7},
        "excerpt": "Anthropic is in talks to raise funding at a $300 billion valuation, sources told Reuters.",
        "extraction_method": "source_snippet",
    },
    {
        "evidence_id": "evidence-9",
        "snapshot_id": "snapshot-0008",
        "source_id": "source-8",
        "locator": {"kind": "snippet", "citation_id": 8},
        "excerpt": "Anthropic is approaching a $30 billion annualized revenue run rate, according to a person familiar with the matter.",
        "extraction_method": "source_snippet",
    },
]

CLAIMS = [
    {
        "claim_id": "claim-1",
        "text": "Anthropic 由 Dario Amodei 与 Daniela Amodei 于 2021 年创立，核心成员多来自 OpenAI，公司定位为 AI 安全与前沿研究机构。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "一、公司概况与融资历程",
        "evidence_ids": ["evidence-1"],
    },
    {
        "claim_id": "claim-2",
        "text": "2025 年 3 月，Anthropic 完成 35 亿美元 E 轮融资，投后估值 615 亿美元。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "一、公司概况与融资历程",
        "evidence_ids": ["evidence-2"],
    },
    {
        "claim_id": "claim-3",
        "text": "Claude Code 于 2025 年 2 月发布，是 Anthropic 面向终端场景的 agent 化编程工具，可直接在命令行中理解并修改代码库。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "二、核心产品与商业模式",
        "evidence_ids": ["evidence-3"],
    },
    {
        "claim_id": "claim-4",
        "text": "Anthropic 于 2024 年 11 月开源 Model Context Protocol（MCP），作为连接 AI 助手与外部数据、工具的统一开放标准。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "二、核心产品与商业模式",
        "evidence_ids": ["evidence-4"],
    },
    {
        "claim_id": "claim-5",
        "text": "Anthropic 于 2025 年 6 月公开其多 agent 研究系统：以 Opus 4 作为主 agent 调度并行子 agent，在内部研究评测上比单 agent 高出 90.2%。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "三、多 agent 研发实践",
        "evidence_ids": ["evidence-5"],
    },
    {
        "claim_id": "claim-6",
        "text": "Amazon 对 Anthropic 的总投资达到 80 亿美元，并基于 Bedrock 平台深度集成 Claude 模型。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "四、市场地位与竞争",
        "evidence_ids": ["evidence-6"],
    },
    {
        "claim_id": "claim-7",
        "text": "Anthropic 多 agent 系统采用 orchestrator-workers 模式：主 agent 将研究主题拆分为并行子任务，子 agent 独立上下文并行检索，并将结果写入文件系统以规避上下文丢失。",
        "criticality": "high",
        "uncertainty": "low",
        "status": "supported",
        "placeholder": False,
        "section_ref": "三、多 agent 研发实践",
        "evidence_ids": ["evidence-7"],
    },
    {
        "claim_id": "claim-8",
        "text": "2025 年 9 月，多家媒体报道 Anthropic 正洽谈以 3000 亿美元估值融资，该轮估值显著高于此前 1370 亿美元的 60 亿美元融资。",
        "criticality": "high",
        "uncertainty": "medium",
        "status": "qualified",
        "placeholder": False,
        "section_ref": "一、公司概况与融资历程",
        "evidence_ids": ["evidence-8"],
    },
    {
        "claim_id": "claim-9",
        "text": "截至 2025 年 9 月，Anthropic 的年化收入运行率接近 300 亿美元（媒体引述知情人士，非官方披露）。",
        "criticality": "medium",
        "uncertainty": "high",
        "status": "qualified",
        "placeholder": False,
        "section_ref": "四、市场地位与竞争",
        "evidence_ids": ["evidence-9"],
    },
    {
        "claim_id": "claim-10",
        "text": "Anthropic 已将 Claude Code 等产品推广至金融、医疗等强监管行业，并以此构建企业级 agent 业务的基本盘。",
        "criticality": "medium",
        "uncertainty": "medium",
        "status": "supported",
        "placeholder": False,
        "section_ref": "二、核心产品与商业模式",
        "evidence_ids": ["evidence-1", "evidence-3"],
    },
    {
        "claim_id": "claim-11",
        "text": "Anthropic 2025 年上半年确认与政府部门在国防与情报领域的合作传闻（具体合同细节无法核实）。",
        "criticality": "high",
        "uncertainty": "high",
        "status": "unsupported",
        "placeholder": False,
        "section_ref": "五、风险与不确定性",
        "evidence_ids": [],
    },
]

EDGES = [
    {
        "edge_id": "edge-1",
        "claim_id": "claim-1",
        "evidence_id": "evidence-1",
        "source_id": "source-1",
        "snapshot_id": "snapshot-0001",
        "locator": {"kind": "snippet", "citation_id": 1},
        "relation": "supported",
        "confidence": 0.95,
        "grounding_status": "grounded",
        "notes": "官方公司页面直接陈述",
    },
    {
        "edge_id": "edge-2",
        "claim_id": "claim-2",
        "evidence_id": "evidence-2",
        "source_id": "source-2",
        "snapshot_id": "snapshot-0002",
        "locator": {"kind": "snippet", "citation_id": 2},
        "relation": "supported",
        "confidence": 0.97,
        "grounding_status": "grounded",
        "notes": "官方融资公告",
    },
    {
        "edge_id": "edge-3",
        "claim_id": "claim-3",
        "evidence_id": "evidence-3",
        "source_id": "source-3",
        "snapshot_id": "snapshot-0003",
        "locator": {"kind": "snippet", "citation_id": 3},
        "relation": "supported",
        "confidence": 0.96,
        "grounding_status": "grounded",
        "notes": "官方发布博客",
    },
    {
        "edge_id": "edge-4",
        "claim_id": "claim-4",
        "evidence_id": "evidence-4",
        "source_id": "source-4",
        "snapshot_id": "snapshot-0004",
        "locator": {"kind": "snippet", "citation_id": 4},
        "relation": "supported",
        "confidence": 0.96,
        "grounding_status": "grounded",
        "notes": "官方发布博客",
    },
    {
        "edge_id": "edge-5",
        "claim_id": "claim-5",
        "evidence_id": "evidence-5",
        "source_id": "source-5",
        "snapshot_id": "snapshot-0005",
        "locator": {"kind": "snippet", "citation_id": 5},
        "relation": "supported",
        "confidence": 0.93,
        "grounding_status": "grounded",
        "notes": "官方工程博客明确给出 90.2% 数字",
    },
    {
        "edge_id": "edge-6",
        "claim_id": "claim-6",
        "evidence_id": "evidence-6",
        "source_id": "source-6",
        "snapshot_id": "snapshot-0006",
        "locator": {"kind": "snippet", "citation_id": 6},
        "relation": "supported",
        "confidence": 0.94,
        "grounding_status": "grounded",
        "notes": "Amazon 官方新闻稿",
    },
    {
        "edge_id": "edge-7",
        "claim_id": "claim-7",
        "evidence_id": "evidence-7",
        "source_id": "source-5",
        "snapshot_id": "snapshot-0005",
        "locator": {"kind": "snippet", "citation_id": 5},
        "relation": "supported",
        "confidence": 0.9,
        "grounding_status": "grounded",
        "notes": "官方工程博客架构描述",
    },
    {
        "edge_id": "edge-8",
        "claim_id": "claim-8",
        "evidence_id": "evidence-8",
        "source_id": "source-7",
        "snapshot_id": "snapshot-0007",
        "locator": {"kind": "snippet", "citation_id": 7},
        "relation": "context_only",
        "confidence": 0.55,
        "grounding_status": "grounded",
        "notes": "单一媒体来源，估值未获公司证实",
    },
    {
        "edge_id": "edge-9",
        "claim_id": "claim-9",
        "evidence_id": "evidence-9",
        "source_id": "source-8",
        "snapshot_id": "snapshot-0008",
        "locator": {"kind": "snippet", "citation_id": 8},
        "relation": "context_only",
        "confidence": 0.45,
        "grounding_status": "grounded",
        "notes": "非官方口径，匿名信源",
    },
    {
        "edge_id": "edge-10",
        "claim_id": "claim-10",
        "evidence_id": "evidence-1",
        "source_id": "source-1",
        "snapshot_id": "snapshot-0001",
        "locator": {"kind": "snippet", "citation_id": 1},
        "relation": "context_only",
        "confidence": 0.6,
        "grounding_status": "grounded",
        "notes": "企业客户信息来自官网概述与产品文档的间接支持",
    },
]

CONFLICT_SETS = [
    {
        "conflict_id": "conflict-1",
        "claim_ids": ["claim-2", "claim-8"],
        "description": "融资估值口径存在时间演进：2025-03 E 轮 615 亿美元 → 2025-06 后 1370 亿美元 → 2025-09 报道洽谈 3000 亿美元。前两项为官方公告，第三项为媒体传闻，报告中以时间线呈现并标注不确定性。",
    },
]


def build_trace() -> list[dict]:
    """Build a scheduler-v2 style event journal that tells the parallel multi-agent story."""
    events: list[dict] = []
    seq = 0

    def add(stage: str, event_type: str, message: str, payload: dict | None = None) -> None:
        nonlocal seq
        seq += 1
        events.append(
            {
                "event_id": f"{JOB_ID}-event-{seq:04d}",
                "job_id": JOB_ID,
                "sequence": seq,
                "stage": stage,
                "event_type": event_type,
                "timestamp": f"2026-08-09T00:00:{seq:02d}.000000+00:00",
                "message": message,
                "payload": payload or {},
            }
        )

    add("job", "job.created", "研究任务已创建", {"topic": PROMPT, "research_profile": "default"})
    add("clarifying", "stage.started", "开始澄清阶段：解析研究意图与边界")
    add(
        "clarifying",
        "clarifying.completed",
        "意图已澄清：公司研究任务，关键目标包括产品线、商业模式、研发实践",
        {"objectives": ["产品线与商业模式", "融资历程与估值", "多 agent 研发实践与行业影响"]},
    )
    add("planned", "stage.started", "开始规划阶段：编译研究计划为任务 DAG")
    for i, objective in enumerate(["产品线与商业模式", "融资历程与估值", "多 agent 研发实践与行业影响"], 1):
        add(
            "planned",
            "task.spawned",
            f"生成研究任务 research-{i}：{objective}",
            {"task_id": f"research-{i}", "role": "researcher", "objective": objective, "parallel": True},
        )
    add("planned", "task.spawned", "生成审计任务 critic-1：对全部研究产出做证据审计", {
        "task_id": "critic-1", "role": "critic", "depends_on": ["research-1", "research-2", "research-3"]
    })
    add("planned", "stage.completed", "任务 DAG 就绪：3 个并行研究任务 + 1 个审计任务", {
        "dag": {"tasks": 4, "parallel_workers": 3}
    })

    tool_events = {
        "research-1": ["官网页", "产品博客", "行业报道"],
        "research-2": ["融资公告", "媒体报道", "估值数据"],
        "research-3": ["工程博客", "开发者社区", "技术分析"],
    }
    add("collecting", "stage.started", "开始收集阶段：3 个 researcher 并行检索")
    for task_id, areas in tool_events.items():
        add(
            "collecting",
            "task.started",
            f"{task_id} 开始执行：并行检索{len(areas)}类来源",
            {"task_id": task_id, "role": "researcher", "workers": 3},
        )
    for i, (task_id, areas) in enumerate(tool_events.items(), 1):
        for area in areas:
            add(
                "collecting",
                "tool.search",
                f"{task_id} 正在检索：{area}",
                {"task_id": task_id, "tool": "web_search", "query": f"Anthropic {area}"},
            )
        add(
            "collecting",
            "tool.page",
            f"{task_id} 读取并快照来源页面",
            {"task_id": task_id, "tool": "page_fetch", "snapshots": len(areas)},
        )
    for task_id in tool_events:
        add(
            "collecting",
            "evidence.collected",
            f"{task_id} 完成证据提取",
            {"task_id": task_id, "evidence_fragments": 4, "selected_sources": 3},
        )
        add("collecting", "task.completed", f"{task_id} 完成", {"task_id": task_id})
    add("collecting", "stage.completed", "3 个研究任务全部完成，共采集 8 个来源")

    add("normalizing", "stage.started", "开始规范化：去重与证据归并")
    add("normalizing", "stage.completed", "证据归并完成：8 个来源、9 个证据片段")
    add("extracting", "stage.started", "开始抽取阶段：从证据中提取结构化 claim")
    for cid, cstatus in [("claim-1", "supported"), ("claim-5", "supported"), ("claim-8", "qualified"), ("claim-11", "unsupported")]:
        add(
            "extracting",
            "claim.extracted",
            f"提取 claim {cid}（{cstatus}）",
            {"claim_id": cid, "criticality": "high", "status": cstatus},
        )
    add("extracting", "stage.completed", "共抽取 11 条 claim")

    add("claim_auditing", "stage.started", "开始审计阶段：构建 claim graph 并执行审计门禁")
    add("claim_auditing", "audit.edge_built", "构建支持边：10 条 claim→证据 关联", {"edges": 10})
    add("claim_auditing", "audit.conflict_detected", "检测到冲突集：融资估值口径随时间演进", {"conflict_sets": 1})
    add(
        "claim_auditing",
        "audit.gate_decision",
        "审计门禁决策：10/11 条 claim 通过，1 条无证据 claim 进入人工复核队列",
        {"gate_status": "passed", "review_queue": ["claim-11"], "precision": 0.91},
    )
    add("claim_auditing", "stage.completed", "审计完成：gate=passed，review_queue=1")

    add("synthesizing", "stage.started", "开始综合阶段：基于通过审计的证据撰写报告")
    add("synthesizing", "stage.completed", "报告初稿完成：5 个章节、10 个带引用段落")
    add("rendering", "stage.started", "开始渲染：编译 report_bundle.json 与 report.md/html")
    add("rendering", "bundle.emitted", "报告 bundle 已产出", {"artifacts": ["report_bundle.json", "report.md", "report.html"]})
    add("completed", "job.completed", "研究任务完成", {"duration_seconds": 312, "sources": 8, "claims": 11})
    return events


REPORT_MD = """# Anthropic 公司研究：Claude 产品线、商业模式与多 agent 研发实践

> 演示案例（demo）：本报告由确定性演示数据生成，用于展示系统的完整产品流程。内容基于 2025 年公开信息整理，不作为投资或商业决策依据。

## 摘要

Anthropic 是 2021 年由前 OpenAI 核心成员创立的 AI 前沿实验室，以"可解释性与安全优先"为立身之本。截至 2025 年底，公司凭借 Claude 模型家族、Claude Code 编程 agent 与 Model Context Protocol（MCP）开放标准，形成了"模型 + 工具 + 生态"的三层商业模式，融资估值从 2025 年 3 月的 615 亿美元一路攀升至年底媒体口径的 1800 亿美元以上。其 2025 年 6 月公开的多 agent 研究系统（比单 agent 高 90.2%）更是把"多 agent 协作"从口号变成了可复现的工程证据。

## 一、公司概况与融资历程

Anthropic 由 Dario Amodei 与 Daniela Amodei 于 2021 年创立，核心成员多来自 OpenAI[1]。公司明确以 AI 安全为使命，优先投入对齐研究，这也成为其在企业客户中建立信任的核心资产。

融资时间线[2][7]：

- 2025-03：E 轮 35 亿美元，投后估值 **615 亿美元**
- 2025-06：60 亿美元融资，估值 **1370 亿美元**
- 2025-09：多家媒体报道正洽谈以 **3000 亿美元** 估值融资（未证实）
- 2025-11：Coatue 领投 20 亿美元，估值 **1800 亿美元**（媒体口径，未证实）

其中 3000 亿美元估值报道与官方口径存在时间差与口径差异，系统在冲突集（conflict set）中标记了该不一致。

## 二、核心产品与商业模式

### Claude 模型家族
Claude 系列从 2023 年的 2.1 迭代至 2025 年的 4.x 家族（Sonnet / Opus / Haiku 分级），覆盖从端侧到旗舰的全价格带。3.5 Sonnet 在 2024 年中期即凭借编码能力获得开发者口碑，Claude 4 进一步强化了工具调用与长上下文能力。

### Claude Code
2025 年 2 月发布的 Claude Code 是面向终端的 agent 化编程工具[3]，可在命令行中理解代码库、执行修改并运行测试。它在开发者社区迅速成为事实标准之一，并成为公司企业收入的重要引擎。

### MCP 协议
2024 年 11 月，Anthropic 开源 Model Context Protocol[4]，为 AI 助手连接外部数据与工具定义了统一标准。MCP 被多家模型厂商与开发框架采纳（包括本项目使用的生态），事实上确立了 agent 工具互操作层。

### 商业模式
三层结构：模型 API（按 token 计费）→ 企业订阅（Claude Pro/Max + 私有部署）→ 生态收入（Claude Code、MCP 生态与 AWS Bedrock 分发）。Amazon 总投资达 80 亿美元并深度集成 Claude[6]。

## 三、多 agent 研发实践（2025 行业标杆）

2025 年 6 月，Anthropic 公开了其多 agent 研究系统[5]，核心发现与设计：

- 架构为 **orchestrator-workers**：主 agent（Opus 4）制定策略并派生并行子 agent（Sonnet 4），子 agent 独立上下文并行检索、压缩汇报
- 量化收益：比单 agent 高 **90.2%**（内部研究评测）；并行化使研究耗时最多下降 **90%**
- 代价透明：多 agent token 成本约为普通 agent 的 15 倍——"更强的能力有明确的价格标签"
- 工程细节：子 agent 直接写文件系统而非层层传话，规避上下文丢失与"电话游戏"失真

这套实践与本项目的设计哲学高度一致：**多 agent 的价值需要被测量，而不是被宣称**。

## 四、市场地位与竞争

- 与 OpenAI（ChatGPT/Deep Research）、Google（Gemini Deep Research）、xAI 正面竞争；Claude 在安全合规、长上下文与企业私有化部署上形成差异化
- 企业客户覆盖金融、医疗、法律等强监管行业
- 2025 年 4 月公司首次确认年化收入超过 10 亿美元；9 月媒体口径接近 300 亿美元运行率[8]（非官方，已标注不确定性）

## 五、风险与不确定性

- 估值与收入口径依赖媒体信源，存在较大不确定性（见冲突集）
- 与政府部门的合作传闻无法核实（对应 claim 未通过审计，已进入人工复核队列）
- 高研发投入与基础设施成本带来的盈利压力

## 参考来源

1. Anthropic — About · 2. Series E 公告 · 3. Claude Code 发布 · 4. MCP 公告 · 5. 多 agent 研究系统工程博客 · 6. Amazon 投资新闻稿 · 7. Reuters 估值报道 · 8. The Information 收入报道
"""


def build_bundle() -> dict:
    return {
        "bundle_version": "1.0.0",
        "demo_notice": "DEMO case. Deterministically generated from authored demo material based on public 2025 information; not a live research result.",
        "job": {
            "job_id": JOB_ID,
            "created_at": "2026-08-09T00:00:00+00:00",
            "input_prompt": PROMPT,
            "status": "demo",
            "current_stage": "completed",
            "source_profile": "company_trusted",
            "budget": {"max_loops": 3, "research_profile": "default", "llm_calls": 24, "search_calls": 18},
            "runtime_path": "scheduler-v2",
            "report_bundle_ref": "bundle/report_bundle.json",
        },
        "citations": [
            {"citation_id": 1, "source_id": "source-1", "snapshot_id": "snapshot-0001", "title": SOURCES[0]["title"]},
            {"citation_id": 2, "source_id": "source-2", "snapshot_id": "snapshot-0002", "title": SOURCES[1]["title"]},
            {"citation_id": 3, "source_id": "source-3", "snapshot_id": "snapshot-0003", "title": SOURCES[2]["title"]},
            {"citation_id": 4, "source_id": "source-4", "snapshot_id": "snapshot-0004", "title": SOURCES[3]["title"]},
            {"citation_id": 5, "source_id": "source-5", "snapshot_id": "snapshot-0005", "title": SOURCES[4]["title"]},
            {"citation_id": 6, "source_id": "source-6", "snapshot_id": "snapshot-0006", "title": SOURCES[5]["title"]},
            {"citation_id": 7, "source_id": "source-7", "snapshot_id": "snapshot-0007", "title": SOURCES[6]["title"]},
            {"citation_id": 8, "source_id": "source-8", "snapshot_id": "snapshot-0008", "title": SOURCES[7]["title"]},
        ],
        "sources": SOURCES,
        "snapshots": [
            {"snapshot_id": f"snapshot-{i:04d}", "source_id": s["source_id"], "content_sha256": f"deadbeef{i:04d}", "size_bytes": 2048 + i * 137}
            for i, s in enumerate(SOURCES, 1)
        ],
        "evidence_fragments": EVIDENCE,
        "audit_summary": {
            "status": "completed",
            "gate_status": "passed",
            "event_count": 56,
            "tool_event_count": 18,
            "stage_event_count": 21,
            "stages": [
                "job", "clarifying", "planned", "collecting", "normalizing",
                "extracting", "claim_auditing", "synthesizing", "rendering", "completed",
            ],
        },
        "audit_events": [
            {"event": "gate.decision", "decision": "passed", "critical_claims": 8, "supported": 7, "qualified": 1, "unsupported": 1},
            {"event": "review_queue.push", "claim_id": "claim-11", "reason": "无可用证据，需人工复核"},
            {"event": "conflict_set.registered", "conflict_id": "conflict-1", "claim_ids": ["claim-2", "claim-8"]},
        ],
        "report_text": REPORT_MD,
        "claims": CLAIMS,
        "claim_support_edges": EDGES,
        "conflict_sets": CONFLICT_SETS,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    bundle_path = OUT_DIR / "report_bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    trace_path = OUT_DIR / "trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
        for event in build_trace():
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    (OUT_DIR / "report.md").write_text(REPORT_MD, encoding="utf-8")
    claims_summary = {
        "total": len(CLAIMS),
        "supported": sum(1 for c in CLAIMS if c["status"] == "supported"),
        "qualified": sum(1 for c in CLAIMS if c["status"] == "qualified"),
        "unsupported": sum(1 for c in CLAIMS if c["status"] == "unsupported"),
    }
    (OUT_DIR / "claims.json").write_text(json.dumps(claims_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"demo case written to {OUT_DIR.relative_to(ROOT)}")
    print(f"claims: {claims_summary}")


if __name__ == "__main__":
    main()
