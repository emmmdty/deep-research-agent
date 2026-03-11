"""LangGraph 研究工作流图定义。

工作流结构：
    Supervisor → Planner → Researcher → Critic ─┐
                              ↑                  │
                              └── (不满足) ──────┘
                              │
                         (满足) → Writer → END

支持迭代研究循环：Critic 评审不满足时，回到 Researcher 执行补充搜索。
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from evaluation.cost_tracker import get_tracker
from agents.supervisor import supervisor_node
from agents.planner import planner_node
from agents.researcher import researcher_node
from agents.critic import critic_node
from agents.writer import writer_node
from workflows.states import ReportArtifact, RunMetrics


def _replace(a, b):
    """状态合并策略：用新值覆盖旧值。"""
    return b


class GraphState(TypedDict, total=False):
    """LangGraph 状态 schema——使用 Annotated 指定合并策略。"""

    research_topic: Annotated[str, _replace]
    tasks: Annotated[list, _replace]
    task_summaries: Annotated[list, _replace]
    sources_gathered: Annotated[list, _replace]
    search_results: Annotated[list, _replace]
    evidence_notes: Annotated[list, _replace]
    critic_feedback: Annotated[Any, _replace]
    loop_count: Annotated[int, _replace]
    max_loops: Annotated[int, _replace]
    final_report: Annotated[Optional[str], _replace]
    report_artifact: Annotated[Optional[ReportArtifact], _replace]
    run_metrics: Annotated[RunMetrics, _replace]
    status: Annotated[str, _replace]
    error: Annotated[Optional[str], _replace]


def _should_continue(state: dict) -> str:
    """条件路由：根据 Critic 反馈决定下一步。

    Returns:
        "continue_research" — 继续迭代研究
        "write_report" — 研究充分，开始撰写报告
    """
    critic_feedback = state.get("critic_feedback")

    if critic_feedback is None:
        return "write_report"

    if critic_feedback.is_sufficient:
        logger.info("✅ 研究质量满足要求，进入报告撰写阶段")
        return "write_report"

    logger.info("🔄 研究质量不足，继续迭代 (score={})", critic_feedback.quality_score)
    return "continue_research"


def build_research_graph():
    """构建研究工作流的 LangGraph 状态图。

    Returns:
        编译后的 LangGraph 状态图。
    """
    # 使用 TypedDict 定义状态 schema
    workflow = StateGraph(GraphState)

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("writer", writer_node)

    # 定义边
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "critic")

    # 条件路由：Critic → Researcher（继续）或 Writer（结束）
    workflow.add_conditional_edges(
        "critic",
        _should_continue,
        {
            "continue_research": "researcher",
            "write_report": "writer",
        },
    )

    workflow.add_edge("writer", END)

    return workflow.compile()


def run_research(topic: str, max_loops: int = 3) -> dict:
    """运行完整的深度研究工作流。

    Args:
        topic: 研究主题。
        max_loops: 最大迭代循环次数。

    Returns:
        最终工作流状态字典，包含 final_report 等。
    """
    logger.info("🚀 启动深度研究: topic='{}', max_loops={}", topic, max_loops)

    graph = build_research_graph()
    tracker = get_tracker()
    owns_tracker = not tracker.is_running
    if owns_tracker:
        tracker.start()

    initial_state: GraphState = {
        "research_topic": topic,
        "tasks": [],
        "task_summaries": [],
        "sources_gathered": [],
        "search_results": [],
        "evidence_notes": [],
        "critic_feedback": None,
        "loop_count": 0,
        "max_loops": max_loops,
        "final_report": None,
        "report_artifact": None,
        "run_metrics": RunMetrics(),
        "status": "initialized",
        "error": None,
    }

    # 执行工作流
    final_state: dict = {}
    try:
        final_state = graph.invoke(initial_state)
    finally:
        metrics = tracker.stop() if owns_tracker else tracker.snapshot()

    run_metrics = RunMetrics(
        time_seconds=round(metrics.total_time_seconds, 2),
        llm_calls=metrics.llm_calls,
        search_calls=metrics.search_calls,
        total_input_tokens=metrics.total_input_tokens,
        total_output_tokens=metrics.total_output_tokens,
        estimated_cost_usd=metrics.estimated_cost_usd,
        status=str(final_state.get("status", "completed")),
    )
    final_state["run_metrics"] = run_metrics
    if final_state.get("report_artifact") is not None:
        final_state["report_artifact"].metrics = run_metrics

    logger.info("🎉 深度研究完成: status={}", final_state.get("status"))
    return final_state
