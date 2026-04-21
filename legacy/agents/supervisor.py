"""Supervisor Agent——顶层协调决策（预留扩展）。

当前版本中，工作流路由由 LangGraph 条件边直接控制。
Supervisor 节点主要负责初始化和状态日志记录。
后续可扩展为基于 LLM 的动态路由决策。
"""

from __future__ import annotations

from loguru import logger


def supervisor_node(state: dict) -> dict:
    """LangGraph 节点：顶层协调初始化。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典。
    """
    research_topic = state["research_topic"]
    logger.info("🎯 Supervisor 启动研究流程: topic='{}'", research_topic)

    return {
        "status": "started",
        "loop_count": 0,
    }
