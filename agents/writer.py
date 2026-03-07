"""Writer Agent——整合所有研究总结，生成最终结构化报告。"""

from __future__ import annotations

from loguru import logger

from llm.provider import get_llm
from prompts.templates import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT
from workflows.states import TaskItem


def writer_node(state: dict) -> dict:
    """LangGraph 节点：生成最终研究报告。

    Args:
        state: 当前工作流状态字典。

    Returns:
        更新后的状态字典，包含 final_report。
    """
    research_topic = state["research_topic"]
    tasks: list[TaskItem] = state.get("tasks", [])
    task_summaries: list[str] = state.get("task_summaries", [])

    logger.info("📝 Writer 开始撰写报告: topic='{}'", research_topic)

    llm = get_llm()

    # 构造任务总结文本
    summaries_text = _format_task_summaries(tasks, task_summaries)

    user_prompt = WRITER_USER_PROMPT.format(
        research_topic=research_topic,
        task_summaries=summaries_text,
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

    logger.info("📝 Writer 报告撰写完成: 长度={} 字符", len(report))

    return {
        "final_report": report,
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
