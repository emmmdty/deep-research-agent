"""LangGraph 工作流状态定义。"""

from __future__ import annotations

from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    """单个研究子任务。"""

    id: int = Field(description="任务编号")
    title: str = Field(description="任务标题")
    intent: str = Field(description="研究意图")
    query: str = Field(description="搜索查询语句")
    status: str = Field(default="pending", description="执行状态")
    summary: Optional[str] = Field(default=None, description="任务总结")
    sources: Optional[str] = Field(default=None, description="来源引用")


class CriticFeedback(BaseModel):
    """Critic Agent 的评估反馈。"""

    quality_score: int = Field(default=0, description="质量评分 0-10")
    is_sufficient: bool = Field(default=False, description="研究是否充分")
    gaps: list[str] = Field(default_factory=list, description="知识空白")
    follow_up_queries: list[str] = Field(default_factory=list, description="补充搜索查询")
    feedback: str = Field(default="", description="整体评价")


class ResearchState(BaseModel):
    """LangGraph 研究工作流的全局状态。

    该状态贯穿整个工作流，由各 Agent 节点读取和更新。
    """

    # 输入
    research_topic: str = Field(description="用户研究主题")

    # 规划阶段
    tasks: list[TaskItem] = Field(default_factory=list, description="研究子任务列表")

    # 执行阶段
    current_task_index: int = Field(default=0, description="当前执行的任务索引")
    search_results: list[str] = Field(default_factory=list, description="各任务的搜索结果")
    task_summaries: list[str] = Field(default_factory=list, description="各任务的总结")
    sources_gathered: list[str] = Field(default_factory=list, description="已收集的来源")

    # 评审阶段
    critic_feedback: Optional[CriticFeedback] = Field(
        default=None, description="Critic 评审反馈"
    )
    loop_count: int = Field(default=0, description="当前迭代次数")
    max_loops: int = Field(default=3, description="最大迭代次数")

    # 报告阶段
    final_report: Optional[str] = Field(default=None, description="最终研究报告")

    # 状态标志
    status: str = Field(default="initialized", description="工作流当前状态")
    error: Optional[str] = Field(default=None, description="错误信息")
