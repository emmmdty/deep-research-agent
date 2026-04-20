"""Writer Agent——整合所有研究总结，生成最终结构化报告。"""

from __future__ import annotations

from loguru import logger

from llm.provider import get_llm
from prompts.templates import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT
from research_policy import build_benchmark_report
from auditor.models import ClaimRecord, ClaimSupportEdgeRecord, ConflictSetRecord, CriticalClaimReviewItem, EvidenceFragmentRecord
from workflows.states import MemoryStats, ReportArtifact, RunMetrics, SourceRecord, TaskItem


def writer_node(state: dict) -> dict:
    """LangGraph 节点：生成最终研究报告。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典，包含 final_report。
    """
    research_topic = state["research_topic"]
    research_profile = state.get("research_profile", "default")
    tasks: list[TaskItem] = [
        task if isinstance(task, TaskItem) else TaskItem.model_validate(task)
        for task in state.get("tasks", [])
    ]
    task_summaries: list[str] = state.get("task_summaries", [])
    sources_gathered: list[SourceRecord] = [
        source if isinstance(source, SourceRecord) else SourceRecord.model_validate(source)
        for source in state.get("sources_gathered", [])
    ]
    evidence_notes = state.get("evidence_notes", [])
    evidence_fragments: list[EvidenceFragmentRecord] = [
        fragment if isinstance(fragment, EvidenceFragmentRecord) else EvidenceFragmentRecord.model_validate(fragment)
        for fragment in state.get("evidence_fragments", [])
    ]
    evidence_units = state.get("evidence_units", [])
    evidence_clusters = state.get("evidence_clusters", [])
    verification_records = state.get("verification_records", [])
    claims: list[ClaimRecord] = [
        claim if isinstance(claim, ClaimRecord) else ClaimRecord.model_validate(claim)
        for claim in state.get("claims", [])
    ]
    claim_support_edges: list[ClaimSupportEdgeRecord] = [
        edge if isinstance(edge, ClaimSupportEdgeRecord) else ClaimSupportEdgeRecord.model_validate(edge)
        for edge in state.get("claim_support_edges", [])
    ]
    conflict_sets: list[ConflictSetRecord] = [
        conflict if isinstance(conflict, ConflictSetRecord) else ConflictSetRecord.model_validate(conflict)
        for conflict in state.get("conflict_sets", [])
    ]
    review_queue: list[CriticalClaimReviewItem] = [
        item if isinstance(item, CriticalClaimReviewItem) else CriticalClaimReviewItem.model_validate(item)
        for item in state.get("critical_claim_review_queue", [])
    ]
    audit_gate_status = str(state.get("audit_gate_status") or "unchecked")
    audit_block_reason = str(state.get("audit_block_reason") or "")
    memory_stats = state.get("memory_stats")
    if memory_stats is None:
        memory_stats = MemoryStats()
    run_metrics = state.get("run_metrics")
    if not isinstance(run_metrics, RunMetrics):
        run_metrics = RunMetrics.model_validate(run_metrics or {})

    logger.info("📝 Writer 开始撰写报告: topic='{}'", research_topic)

    if research_profile == "benchmark":
        report = build_benchmark_report(
            topic=research_topic,
            tasks=tasks,
            task_summaries=task_summaries,
            sources=sources_gathered,
            evidence_notes=evidence_notes,
        )
    else:
        llm = get_llm()

        # 构造任务总结文本
        summaries_text = _format_task_summaries(tasks, task_summaries)

        user_prompt = WRITER_USER_PROMPT.format(
            research_topic=research_topic,
            task_summaries=summaries_text,
            source_catalog=_format_source_catalog(sources_gathered),
        )

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        report = response.content

        # 清理模型思维链泄露（<think>标签等）
        from llm.clean import clean_llm_output

        report = clean_llm_output(report)

    if audit_gate_status == "blocked":
        report = _prepend_audit_block_notice(report, review_queue, conflict_sets, audit_block_reason)

    logger.info("📝 Writer 报告撰写完成: 长度={} 字符", len(report))

    return {
        "final_report": report,
        "report_artifact": ReportArtifact(
            topic=research_topic,
            report=report,
            citations=sources_gathered,
            evidence_notes=evidence_notes,
            evidence_fragments=evidence_fragments,
            evidence_units=evidence_units,
            evidence_clusters=evidence_clusters,
            verification_records=verification_records,
            claims=claims,
            claim_support_edges=claim_support_edges,
            conflict_sets=conflict_sets,
            critical_claim_review_queue=review_queue,
            audit_gate_status=audit_gate_status,
            audit_block_reason=audit_block_reason,
            memory_stats=memory_stats,
            metrics=run_metrics,
        ),
        "status": "completed",
    }


def _format_task_summaries(tasks: list[TaskItem], summaries: list[str]) -> str:
    """将任务和总结格式化为 Writer 可用的文本。"""
    parts = []
    for i, summary in enumerate(summaries):
        if i < len(tasks):
            task = tasks[i]
            parts.append(
                f"### 子任务 {task.id}: {task.title}\n"
                f"- 研究意图: {task.intent}\n"
                f"- 搜索查询: {task.query}\n\n"
                f"{summary}\n"
            )
        else:
            # 补充搜索的总结
            parts.append(f"### 补充研究 {i + 1}\n\n{summary}\n")

    return "\n---\n\n".join(parts) if parts else "暂无研究总结"


def _format_source_catalog(sources: list[SourceRecord]) -> str:
    """格式化来源清单。"""
    if not sources:
        return "暂无来源。"

    return "\n".join(
        f"[{source.citation_id}] {source.title} - {source.url}"
        for source in sources
    )


def _prepend_audit_block_notice(
    report: str,
    review_queue: list[CriticalClaimReviewItem],
    conflict_sets: list[ConflictSetRecord],
    audit_block_reason: str,
) -> str:
    """在报告顶部插入 claim 审计阻塞说明。"""
    lines = [
        "> 审计门禁：存在未通过审核的关键 claim，以下内容不可视为已完全验证的研究结论。",
    ]
    if audit_block_reason:
        lines.append(f"> 阻塞原因：{audit_block_reason}")
    if review_queue:
        lines.append("")
        lines.append("## 待复核关键 Claim")
        for item in review_queue:
            lines.append(f"- {item.text}（{item.reason}）")
    if conflict_sets:
        lines.append("")
        lines.append("## 冲突与不确定性")
        for conflict in conflict_sets:
            lines.append(f"- {conflict.summary}")
    lines.append("")
    return "\n".join(lines) + report
