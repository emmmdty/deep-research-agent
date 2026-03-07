"""Planner Agent——将研究主题拆解为可执行的子任务。"""

from __future__ import annotations

import json

from loguru import logger

from llm.provider import get_llm
from prompts.templates import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT, get_current_date
from workflows.states import ResearchState, TaskItem


def planner_node(state: dict) -> dict:
    """LangGraph 节点：调用 Planner Agent 生成研究计划。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典，包含 tasks 列表。
    """
    research_topic = state["research_topic"]
    logger.info("📋 Planner 开始规划: topic='{}'", research_topic)

    llm = get_llm()

    # 构造提示词
    user_prompt = PLANNER_USER_PROMPT.format(
        current_date=get_current_date(),
        research_topic=research_topic,
    )

    # 调用 LLM
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    raw_text = response.content

    # 清理模型思维链泄露
    from llm.clean import extract_json_from_output
    raw_text = extract_json_from_output(raw_text)

    # 解析 JSON
    tasks = _extract_tasks(raw_text, research_topic)
    logger.info("📋 Planner 规划完成: 生成 {} 个子任务", len(tasks))

    return {
        "tasks": tasks,
        "status": "planned",
    }


def _extract_tasks(raw_text: str, fallback_topic: str) -> list[TaskItem]:
    """从 LLM 响应中解析任务列表。"""
    try:
        # 尝试直接解析
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 片段
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end > start:
            try:
                payload = json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("Planner 输出解析失败，使用默认任务")
                return [_fallback_task(fallback_topic)]
        else:
            logger.warning("Planner 输出无 JSON，使用默认任务")
            return [_fallback_task(fallback_topic)]

    # 提取 tasks 列表
    task_list = payload.get("tasks", payload) if isinstance(payload, dict) else payload
    if not isinstance(task_list, list):
        return [_fallback_task(fallback_topic)]

    tasks = []
    for i, item in enumerate(task_list, 1):
        if not isinstance(item, dict):
            continue
        tasks.append(
            TaskItem(
                id=i,
                title=str(item.get("title", f"任务{i}")),
                intent=str(item.get("intent", "深入研究")),
                query=str(item.get("query", fallback_topic)),
            )
        )

    return tasks if tasks else [_fallback_task(fallback_topic)]


def _fallback_task(topic: str) -> TaskItem:
    """生成默认回退任务。"""
    return TaskItem(
        id=1,
        title="基础背景梳理",
        intent="收集主题核心背景与最新动态",
        query=f"{topic} 最新进展",
    )
