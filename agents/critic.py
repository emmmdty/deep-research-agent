"""Critic Agent——评估研究质量，决定是否需要继续迭代。"""

from __future__ import annotations

import json

from loguru import logger

from llm.provider import get_llm
from prompts.templates import CRITIC_SYSTEM_PROMPT, CRITIC_USER_PROMPT
from workflows.states import CriticFeedback


def critic_node(state: dict) -> dict:
    """LangGraph 节点：评审当前研究结果的质量。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典，包含 critic_feedback。
    """
    research_topic = state["research_topic"]
    task_summaries = state.get("task_summaries", [])
    sources_gathered = state.get("sources_gathered", [])
    loop_count = state.get("loop_count", 0)
    max_loops = state.get("max_loops", 3)

    logger.info("🔍 Critic 开始评审: loop={}/{}", loop_count + 1, max_loops)

    llm = get_llm()

    # 构造上下文
    summaries_text = "\n\n---\n\n".join(task_summaries) if task_summaries else "暂无总结"
    sources_text = "\n\n".join(sources_gathered[:5]) if sources_gathered else "暂无来源"

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
