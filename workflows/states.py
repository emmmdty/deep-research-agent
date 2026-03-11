"""LangGraph 工作流状态定义。"""

from __future__ import annotations

from typing import Any, Optional

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
    strategy: str = Field(default="multi_source", description="执行策略")


class SourceRecord(BaseModel):
    """结构化来源记录。"""

    citation_id: int = Field(description="报告中的引用编号")
    source_type: str = Field(description="来源类型，例如 web/github/arxiv")
    query: str = Field(description="触发该来源的搜索查询")
    title: str = Field(description="来源标题")
    url: str = Field(default="", description="来源链接")
    snippet: str = Field(default="", description="来源摘要")
    task_title: str = Field(default="", description="所属任务标题")
    published_at: Optional[str] = Field(default=None, description="发布时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class EvidenceNote(BaseModel):
    """研究证据笔记。"""

    task_id: Optional[int] = Field(default=None, description="所属任务 ID")
    task_title: str = Field(default="", description="所属任务标题")
    query: str = Field(description="搜索查询")
    summary: str = Field(description="该轮研究总结")
    source_ids: list[int] = Field(default_factory=list, description="支撑该总结的来源编号")


class RunMetrics(BaseModel):
    """单次研究运行指标。"""

    time_seconds: float = Field(default=0.0, description="总耗时（秒）")
    llm_calls: int = Field(default=0, description="LLM 调用次数")
    search_calls: int = Field(default=0, description="搜索调用次数")
    total_input_tokens: int = Field(default=0, description="输入 token 数")
    total_output_tokens: int = Field(default=0, description="输出 token 数")
    estimated_cost_usd: float = Field(default=0.0, description="估算美元成本")
    status: str = Field(default="initialized", description="运行状态")

    @property
    def total_tokens(self) -> int:
        """总 token 数。"""
        return self.total_input_tokens + self.total_output_tokens


class ReportArtifact(BaseModel):
    """结构化报告产物。"""

    topic: str = Field(description="研究主题")
    report: str = Field(description="最终 Markdown 报告")
    citations: list[SourceRecord] = Field(default_factory=list, description="引用来源")
    evidence_notes: list[EvidenceNote] = Field(default_factory=list, description="证据笔记")
    metrics: RunMetrics = Field(default_factory=RunMetrics, description="运行指标")


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
    sources_gathered: list[SourceRecord] = Field(default_factory=list, description="已收集的来源")
    evidence_notes: list[EvidenceNote] = Field(default_factory=list, description="结构化证据笔记")
    run_metrics: RunMetrics = Field(default_factory=RunMetrics, description="运行指标")

    # 评审阶段
    critic_feedback: Optional[CriticFeedback] = Field(
        default=None, description="Critic 评审反馈"
    )
    loop_count: int = Field(default=0, description="当前迭代次数")
    max_loops: int = Field(default=3, description="最大迭代次数")

    # 报告阶段
    final_report: Optional[str] = Field(default=None, description="最终研究报告")
    report_artifact: Optional[ReportArtifact] = Field(default=None, description="结构化报告产物")

    # 状态标志
    status: str = Field(default="initialized", description="工作流当前状态")
    error: Optional[str] = Field(default=None, description="错误信息")
