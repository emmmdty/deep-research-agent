"""LangGraph 工作流状态定义。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from deep_research_agent.auditor.models import (
    ClaimRecord,
    ClaimSupportEdgeRecord,
    ConflictSetRecord,
    CriticalClaimReviewItem,
    EvidenceFragmentRecord,
)


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
    task_type: str = Field(default="research", description="任务类型")
    expected_aspects: list[str] = Field(default_factory=list, description="该任务负责覆盖的方面")
    preferred_sources: list[str] = Field(default_factory=list, description="优先来源")
    must_include_terms: list[str] = Field(default_factory=list, description="检索必须包含的术语")
    avoid_terms: list[str] = Field(default_factory=list, description="应避免的术语")
    recommended_capabilities: list[str] = Field(
        default_factory=list,
        description="推荐能力列表，格式如 web.search / skill.install-guide",
    )


class TopicSpec(BaseModel):
    """研究主题的结构化规格。"""

    id: str = Field(default="custom", description="主题 ID")
    topic: str = Field(description="研究主题")
    difficulty: str = Field(default="medium", description="难度")
    expected_aspects: list[str] = Field(default_factory=list, description="预期覆盖方面")
    min_sources: int = Field(default=0, description="最低来源数")
    min_words: int = Field(default=0, description="最低字数")


class SkillDefinition(BaseModel):
    """兼容 Claude Code 风格目录组织的 skill 定义。"""

    name: str = Field(description="skill 名称")
    description: str = Field(default="", description="skill 描述")
    path: str = Field(description="skill 目录路径")
    body: str = Field(default="", description="skill 正文")
    triggers: list[str] = Field(default_factory=list, description="触发关键字")


class MCPToolDefinition(BaseModel):
    """单个 MCP 工具定义。"""

    name: str = Field(description="工具名")
    description: str = Field(default="", description="工具描述")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="输入 schema")


class MCPServerConfig(BaseModel):
    """MCP server 配置。"""

    name: str = Field(description="server 名称")
    transport: str = Field(default="stdio", description="连接方式：stdio / sse / streamable-http")
    command: Optional[str] = Field(default=None, description="stdio 启动命令")
    args: list[str] = Field(default_factory=list, description="stdio 参数")
    url: Optional[str] = Field(default=None, description="远程 MCP 地址")
    env: dict[str, str] = Field(default_factory=dict, description="stdio 环境变量")
    headers_env: dict[str, str] = Field(default_factory=dict, description="HTTP 请求头到环境变量名的映射")
    auth_env: Optional[str] = Field(default=None, description="Bearer Token 的环境变量名")
    timeout_seconds: float = Field(default=10.0, description="连接超时")
    tool_allowlist: list[str] = Field(default_factory=list, description="允许暴露的工具名")
    tool_denylist: list[str] = Field(default_factory=list, description="禁止暴露的工具名")
    enabled: bool = Field(default=True, description="是否启用该 server")
    tools: list[MCPToolDefinition] = Field(default_factory=list, description="静态工具定义")


class ToolCapability(BaseModel):
    """统一能力定义。"""

    name: str = Field(description="能力名")
    kind: str = Field(description="builtin / skill / mcp")
    description: str = Field(default="", description="能力描述")
    source_type: str = Field(default="", description="关联来源类型")
    tags: list[str] = Field(default_factory=list, description="能力标签")
    priority: int = Field(default=0, description="路由优先级")
    enabled: bool = Field(default=True, description="是否启用")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ToolInvocationRecord(BaseModel):
    """单次能力调用记录。"""

    capability_name: str = Field(description="能力名")
    kind: str = Field(description="能力类型")
    task_title: str = Field(default="", description="所属任务")
    success: bool = Field(default=True, description="是否成功")
    detail: str = Field(default="", description="调用说明")


class EvidenceUnit(BaseModel):
    """最小证据单元。"""

    id: str = Field(description="证据 ID")
    claim: str = Field(description="核心主张")
    snippet: str = Field(default="", description="证据片段")
    source_id: int = Field(description="来源编号")
    snapshot_ref: str = Field(default="", description="来源快照引用")
    source_type: str = Field(description="来源类型")
    task_title: str = Field(default="", description="任务标题")
    url: str = Field(default="", description="来源链接")
    trust_tier: int = Field(default=3, description="可信度等级")
    support_type: str = Field(default="supported", description="supported / weakly_supported / conflicting")


class EvidenceCluster(BaseModel):
    """跨源证据聚类。"""

    id: str = Field(description="聚类 ID")
    claim: str = Field(description="聚类主张")
    evidence_ids: list[str] = Field(default_factory=list, description="聚类内证据")
    source_ids: list[int] = Field(default_factory=list, description="来源编号")
    support_count: int = Field(default=0, description="支持来源数")
    conflict_count: int = Field(default=0, description="冲突来源数")
    high_trust_count: int = Field(default=0, description="高可信来源数")


class VerificationRecord(BaseModel):
    """段落或任务级验证记录。"""

    task_title: str = Field(default="", description="任务标题")
    citation_ids: list[int] = Field(default_factory=list, description="关联来源编号")
    status: str = Field(default="supported", description="supported / weakly_supported / conflicting")
    notes: str = Field(default="", description="验证说明")


class MemoryStats(BaseModel):
    """证据记忆统计。"""

    total_evidence_units: int = Field(default=0, description="证据单元数")
    total_clusters: int = Field(default=0, description="聚类数")
    high_trust_evidence_units: int = Field(default=0, description="高可信证据数")
    high_trust_ratio: float = Field(default=0.0, description="高可信证据占比")
    conflict_count: int = Field(default=0, description="冲突计数")
    entity_consistency_score: float = Field(default=1.0, description="实体一致性得分")


class SourceRecord(BaseModel):
    """结构化来源记录。"""

    citation_id: int = Field(description="报告中的引用编号")
    source_id: str = Field(default="", description="来源文档 ID")
    source_type: str = Field(description="来源类型，例如 web/github/arxiv")
    query: str = Field(description="触发该来源的搜索查询")
    title: str = Field(description="来源标题")
    canonical_uri: str = Field(default="", description="归一化来源 URI")
    url: str = Field(default="", description="来源链接")
    snippet: str = Field(default="", description="来源摘要")
    task_title: str = Field(default="", description="所属任务标题")
    published_at: Optional[str] = Field(default=None, description="发布时间")
    snapshot_ref: str = Field(default="", description="来源快照引用")
    fetched_at: Optional[str] = Field(default=None, description="抓取时间")
    mime_type: str = Field(default="text/plain", description="抓取内容 MIME 类型")
    auth_scope: str = Field(default="public", description="鉴权范围")
    freshness_metadata: dict[str, Any] = Field(default_factory=dict, description="新鲜度元数据")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    trust_tier: int = Field(default=3, description="来源可信度等级，1-5")
    relevance_score: float = Field(default=0.0, description="相关性得分")
    selection_score: float = Field(default=0.0, description="最终选择得分")
    selected: bool = Field(default=True, description="是否被选入总结")
    rejection_reason: Optional[str] = Field(default=None, description="被过滤原因")


class EvidenceNote(BaseModel):
    """研究证据笔记。"""

    task_id: Optional[int] = Field(default=None, description="所属任务 ID")
    task_title: str = Field(default="", description="所属任务标题")
    query: str = Field(description="搜索查询")
    summary: str = Field(description="该轮研究总结")
    source_ids: list[int] = Field(default_factory=list, description="支撑该总结的来源编号")
    aspect_hits: list[str] = Field(default_factory=list, description="本轮命中的方面")
    claim_count: int = Field(default=0, description="核心发现条数")
    selected_source_ids: list[int] = Field(default_factory=list, description="实际选入的来源编号")


class RunMetrics(BaseModel):
    """单次研究运行指标。"""

    time_seconds: float = Field(default=0.0, description="总耗时（秒）")
    llm_calls: int = Field(default=0, description="LLM 调用次数")
    search_calls: int = Field(default=0, description="搜索调用次数")
    total_input_tokens: int = Field(default=0, description="输入 token 数")
    total_output_tokens: int = Field(default=0, description="输出 token 数")
    estimated_cost_usd: float = Field(default=0.0, description="估算美元成本")
    status: str = Field(default="initialized", description="运行状态")
    selected_sources: int = Field(default=0, description="被选中来源数")
    rejected_sources: int = Field(default=0, description="被过滤来源数")
    fallback_search_calls: int = Field(default=0, description="搜索后端回退次数")
    quality_gate_status: str = Field(default="unchecked", description="质量门控状态")
    quality_gate_fail_reason: str = Field(default="", description="质量门控失败原因")
    case_study_query_count: int = Field(default=0, description="case-study 查询次数")
    case_study_rescue_calls: int = Field(default=0, description="case-study 补救检索次数")
    summary_repair_count: int = Field(default=0, description="benchmark summary 自动修复次数")
    summary_repair_tasks: list[str] = Field(default_factory=list, description="触发 summary 修复的任务标题")
    skill_activation_count: int = Field(default=0, description="skill 激活次数")
    mcp_activation_count: int = Field(default=0, description="MCP 能力激活次数")
    tool_use_success_rate: float = Field(default=0.0, description="工具调用成功率")
    linked_sources_discovered: int = Field(default=0, description="从已抓取来源中发现的高价值子来源数")
    linked_sources_fetched: int = Field(default=0, description="成功抓取的高价值子来源数")
    remote_pdfs_ingested: int = Field(default=0, description="成功解析的远程 PDF 数")
    audit_rescue_queries: int = Field(default=0, description="claim audit 触发的补采查询数")
    policy_blocked_child_links: int = Field(default=0, description="被 source policy 拦截的子链接数")

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
    evidence_fragments: list[EvidenceFragmentRecord] = Field(default_factory=list, description="证据片段")
    evidence_units: list[EvidenceUnit] = Field(default_factory=list, description="证据单元")
    evidence_clusters: list[EvidenceCluster] = Field(default_factory=list, description="证据聚类")
    verification_records: list[VerificationRecord] = Field(default_factory=list, description="验证记录")
    claims: list[ClaimRecord] = Field(default_factory=list, description="claim 图节点")
    claim_support_edges: list[ClaimSupportEdgeRecord] = Field(default_factory=list, description="claim 与 evidence 的边")
    conflict_sets: list[ConflictSetRecord] = Field(default_factory=list, description="冲突集合")
    critical_claim_review_queue: list[CriticalClaimReviewItem] = Field(default_factory=list, description="关键 claim 复核队列")
    audit_gate_status: str = Field(default="unchecked", description="审计门禁状态")
    audit_block_reason: str = Field(default="", description="审计阻塞原因")
    memory_stats: MemoryStats = Field(default_factory=MemoryStats, description="记忆统计")
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
    job_id: str = Field(default="", description="当前 orchestrator job ID")
    topic_spec: Optional[TopicSpec] = Field(default=None, description="结构化主题规格")
    research_profile: str = Field(default="default", description="运行 profile")
    ablation_variant: Optional[str] = Field(default=None, description="ablation 变体名称")
    source_profile: str = Field(default="open-web", description="来源策略 profile")
    policy_overrides: dict[str, Any] = Field(default_factory=dict, description="job 级策略覆盖")
    file_inputs: list[str] = Field(default_factory=list, description="内部文件输入路径")
    job_workspace_dir: str = Field(default="", description="当前 job 专属工作目录")

    # 规划阶段
    tasks: list[TaskItem] = Field(default_factory=list, description="研究子任务列表")

    # 执行阶段
    current_task_index: int = Field(default=0, description="当前执行的任务索引")
    search_results: list[str] = Field(default_factory=list, description="各任务的搜索结果")
    task_summaries: list[str] = Field(default_factory=list, description="各任务的总结")
    sources_gathered: list[SourceRecord] = Field(default_factory=list, description="已收集的来源")
    source_snapshots: list[dict[str, Any]] = Field(default_factory=list, description="来源快照清单")
    discovered_source_candidates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="从已抓取来源中发现的候选子来源",
    )
    visited_source_uris: list[str] = Field(default_factory=list, description="已抓取或已排队的来源 URI")
    blocked_source_candidates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="被 source policy 或安全策略拦截的候选来源",
    )
    evidence_notes: list[EvidenceNote] = Field(default_factory=list, description="结构化证据笔记")
    evidence_fragments: list[EvidenceFragmentRecord] = Field(default_factory=list, description="证据片段")
    evidence_units: list[EvidenceUnit] = Field(default_factory=list, description="证据单元")
    evidence_clusters: list[EvidenceCluster] = Field(default_factory=list, description="证据聚类")
    verification_records: list[VerificationRecord] = Field(default_factory=list, description="验证记录")
    claims: list[ClaimRecord] = Field(default_factory=list, description="claim 图节点")
    claim_support_edges: list[ClaimSupportEdgeRecord] = Field(default_factory=list, description="claim 与证据边")
    conflict_sets: list[ConflictSetRecord] = Field(default_factory=list, description="冲突集合")
    critical_claim_review_queue: list[CriticalClaimReviewItem] = Field(default_factory=list, description="关键 claim 复核队列")
    memory_stats: MemoryStats = Field(default_factory=MemoryStats, description="记忆统计")
    available_capabilities: list[ToolCapability] = Field(default_factory=list, description="当前能力注册表")
    capability_plan: dict[str, list[str]] = Field(default_factory=dict, description="任务到能力的映射")
    tool_invocations: list[ToolInvocationRecord] = Field(default_factory=list, description="工具调用记录")
    connector_health: dict[str, Any] = Field(default_factory=dict, description="connector 健康统计")
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
    coverage_status: dict[str, bool] = Field(default_factory=dict, description="方面覆盖状态")
    quality_gate_status: str = Field(default="unchecked", description="质量门控状态")
    quality_gate_fail_reason: str = Field(default="", description="质量门控失败原因")
    pending_follow_up_queries: list[str] = Field(default_factory=list, description="待执行的补充查询")
    refinement_history: list[dict[str, Any]] = Field(default_factory=list, description="显式 refinement 记录")
    audit_gate_status: str = Field(default="unchecked", description="审计门禁状态")
    audit_block_reason: str = Field(default="", description="审计阻塞原因")
    critical_claim_count: int = Field(default=0, description="关键 claim 数")
    blocked_critical_claim_count: int = Field(default=0, description="阻塞中的关键 claim 数")
    audit_graph_path: str = Field(default="", description="claim graph 文件路径")
    review_queue_path: str = Field(default="", description="review queue 文件路径")

    # 状态标志
    status: str = Field(default="initialized", description="工作流当前状态")
    error: Optional[str] = Field(default=None, description="错误信息")
