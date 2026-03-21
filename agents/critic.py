"""Critic Agent——评估研究质量，决定是否需要继续迭代。"""

from __future__ import annotations

import json

from loguru import logger

from llm.provider import get_llm
from prompts.templates import CRITIC_SYSTEM_PROMPT, CRITIC_USER_PROMPT
from research_policy import evaluate_quality_gate
from workflows.states import CriticFeedback, RunMetrics, SourceRecord, TaskItem


def critic_node(state: dict) -> dict:
    """LangGraph 节点：评审当前研究结果的质量。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典，包含 critic_feedback。
    """
    research_topic = state["research_topic"]
    research_profile = state.get("research_profile", "default")
    ablation_variant = state.get("ablation_variant")
    task_summaries = state.get("task_summaries", [])
    sources_gathered: list[SourceRecord] = state.get("sources_gathered", [])
    tasks: list[TaskItem] = state.get("tasks", [])
    memory_stats = state.get("memory_stats")
    loop_count = state.get("loop_count", 0)
    max_loops = state.get("max_loops", 3)
    run_metrics = state.get("run_metrics")
    if not isinstance(run_metrics, RunMetrics):
        run_metrics = RunMetrics.model_validate(run_metrics or {})

    logger.info("🔍 Critic 开始评审: loop={}/{}", loop_count + 1, max_loops)

    if research_profile == "benchmark":
        if ablation_variant in {"ours_base", "ours_verifier"}:
            feedback = CriticFeedback(
                quality_score=6,
                is_sufficient=True,
                gaps=[],
                follow_up_queries=[],
                feedback="该 ablation 变体禁用了 quality gate，直接进入写作阶段。",
            )
            run_metrics.quality_gate_status = "skipped"
            return {
                "critic_feedback": feedback,
                "loop_count": loop_count + 1,
                "quality_gate_status": "skipped",
                "run_metrics": run_metrics,
                "status": "reviewed",
            }
        gate = evaluate_quality_gate(
            tasks=tasks,
            task_summaries=task_summaries,
            sources=sources_gathered,
            loop_count=loop_count,
            max_loops=max_loops,
            research_topic=research_topic,
        )
        if getattr(memory_stats, "entity_consistency_score", 1.0) < 0.8:
            gate["passed"] = False
            gate["quality_gate_status"] = "failed"
            gate["missing_aspects"].append("实体一致性不足")
            gate["follow_up_queries"].append(f"{research_topic} official documentation canonical definition")
            fail_reason = gate.get("quality_gate_fail_reason", "")
            gate["quality_gate_fail_reason"] = "；".join(
                item for item in [fail_reason, "实体一致性不足"] if item
            )
        feedback = CriticFeedback(
            quality_score=8 if gate["passed"] else 5,
            is_sufficient=bool(gate["passed"]),
            gaps=list(gate["missing_aspects"]),
            follow_up_queries=list(gate["follow_up_queries"]),
            feedback=(
                "研究覆盖满足 benchmark 质量门槛。"
                if gate["passed"]
                else (
                    f"质量门控未通过：{gate.get('quality_gate_fail_reason') or '仍缺少关键方面'}。"
                    if gate["quality_gate_status"] == "failed"
                    else f"仍缺少关键方面：{', '.join(gate['missing_aspects']) or '无'}。"
                )
            ),
        )
        run_metrics.quality_gate_status = gate["quality_gate_status"]
        run_metrics.quality_gate_fail_reason = str(gate.get("quality_gate_fail_reason") or "")
        logger.info(
            "🔍 Critic benchmark 评审完成: status={}, sufficient={}, gaps={}",
            gate["quality_gate_status"],
            feedback.is_sufficient,
            len(feedback.gaps),
        )
        return {
            "critic_feedback": feedback,
            "loop_count": loop_count + 1,
            "quality_gate_status": gate["quality_gate_status"],
            "quality_gate_fail_reason": str(gate.get("quality_gate_fail_reason") or ""),
            "run_metrics": run_metrics,
            "status": "reviewed",
        }

    llm = get_llm()

    # 构造上下文
    summaries_text = "\n\n---\n\n".join(task_summaries) if task_summaries else "暂无总结"
    if sources_gathered:
        source_lines = []
        for source in sources_gathered[:5]:
            source_lines.append(
                f"[{source.citation_id}] ({source.source_type}) {source.title}\n"
                f"URL: {source.url}\n"
                f"摘要: {source.snippet}"
            )
        sources_text = "\n\n".join(source_lines)
    else:
        sources_text = "暂无来源"

    user_prompt = CRITIC_USER_PROMPT.format(
        research_topic=research_topic,
        summaries=summaries_text,
        sources=sources_text,
        loop_count=loop_count + 1,
        max_loops=max_loops,
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    raw_text = response.content

    # 清理模型思维链泄露
    from llm.clean import extract_json_from_output
    raw_text = extract_json_from_output(raw_text)

    # 解析反馈
    feedback = _parse_feedback(raw_text)

    # 达到最大迭代次数时强制通过
    if loop_count + 1 >= max_loops:
        feedback.is_sufficient = True
        logger.info("🔍 Critic: 达到最大迭代次数，强制通过")

    logger.info(
        "🔍 Critic 评审完成: score={}, sufficient={}, gaps={}",
        feedback.quality_score,
        feedback.is_sufficient,
        len(feedback.gaps),
    )

    return {
        "critic_feedback": feedback,
        "loop_count": loop_count + 1,
        "run_metrics": run_metrics,
        "status": "reviewed",
    }


def _parse_feedback(raw_text: str) -> CriticFeedback:
    """从 LLM 响应中解析 Critic 反馈。"""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 片段
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end > start:
            try:
                payload = json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("Critic 输出解析失败，默认通过")
                return CriticFeedback(
                    quality_score=7,
                    is_sufficient=True,
                    feedback="无法解析评审结果，默认通过",
                )
        else:
            return CriticFeedback(
                quality_score=7,
                is_sufficient=True,
                feedback="无法解析评审结果，默认通过",
            )

    return CriticFeedback(
        quality_score=int(payload.get("quality_score", 7)),
        is_sufficient=bool(payload.get("is_sufficient", True)),
        gaps=list(payload.get("gaps", [])),
        follow_up_queries=list(payload.get("follow_up_queries", [])),
        feedback=str(payload.get("feedback", "")),
    )
