"""Researcher Agent——执行搜索并总结每个子任务的研究结果。"""

from __future__ import annotations

from loguru import logger

from llm.provider import get_llm
from prompts.templates import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT
from tools.web_search import web_search_tool
from workflows.states import TaskItem


def researcher_node(state: dict) -> dict:
    """LangGraph 节点：对每个未完成的子任务执行搜索和总结。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典。
    """
    tasks: list[TaskItem] = state.get("tasks", [])
    research_topic = state["research_topic"]
    task_summaries: list[str] = list(state.get("task_summaries", []))
    sources_gathered: list[str] = list(state.get("sources_gathered", []))
    search_results: list[str] = list(state.get("search_results", []))

    # 处理 Critic 反馈中的补充查询
    critic_feedback = state.get("critic_feedback")
    follow_up_queries: list[str] = []
    if critic_feedback and hasattr(critic_feedback, "follow_up_queries"):
        follow_up_queries = critic_feedback.follow_up_queries

    llm = get_llm()

    if follow_up_queries:
        # 迭代模式：执行补充搜索
        logger.info("🔄 Researcher 执行补充搜索: {} 个查询", len(follow_up_queries))
        for query in follow_up_queries:
            _execute_single_search(
                query=query,
                task_title=f"补充研究",
                task_intent="填充知识空白",
                research_topic=research_topic,
                llm=llm,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                search_results=search_results,
            )
    else:
        # 首次执行：处理所有子任务
        logger.info("🔍 Researcher 开始执行 {} 个子任务", len(tasks))
        for task in tasks:
            if task.status == "completed":
                continue

            _execute_single_search(
                query=task.query,
                task_title=task.title,
                task_intent=task.intent,
                research_topic=research_topic,
                llm=llm,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                search_results=search_results,
            )
            task.status = "completed"

    logger.info("🔍 Researcher 执行完成: 总结数={}", len(task_summaries))

    return {
        "tasks": tasks,
        "task_summaries": task_summaries,
        "sources_gathered": sources_gathered,
        "search_results": search_results,
        "status": "researched",
    }


def _execute_single_search(
    *,
    query: str,
    task_title: str,
    task_intent: str,
    research_topic: str,
    llm,
    task_summaries: list[str],
    sources_gathered: list[str],
    search_results: list[str],
) -> None:
    """执行单个搜索 + 总结流程。"""
    logger.info("  🔎 搜索: '{}'", query)

    # 搜索
    search_result = web_search_tool.invoke({"query": query, "max_results": 5})
    search_results.append(search_result)

    if not search_result or search_result.startswith("搜索失败") or search_result.startswith("搜索未返回"):
        logger.warning("  ⚠️ 搜索无结果: '{}'", query)
        task_summaries.append(f"## {task_title}\n\n暂无可用信息。\n")
        return

    sources_gathered.append(search_result)

    # 总结
    user_prompt = SUMMARIZER_USER_PROMPT.format(
        research_topic=research_topic,
        task_title=task_title,
        task_intent=task_intent,
        task_query=query,
        context=search_result,
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    summary = response.content

    # 清理模型思维链泄露
    from llm.clean import clean_llm_output
    summary = clean_llm_output(summary)

    task_summaries.append(summary)
    logger.info("  ✅ 总结完成: '{}'", task_title)
