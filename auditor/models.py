"""Phase 04 审计数据对象。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """返回 UTC ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


class EvidenceFragmentRecord(BaseModel):
    """可审计的证据片段。"""

    evidence_id: str = Field(description="证据片段 ID")
    snapshot_id: str = Field(description="来源快照 ID")
    source_id: str = Field(description="来源文档 ID")
    locator: dict[str, Any] = Field(default_factory=dict, description="片段定位信息")
    excerpt: str = Field(default="", description="片段摘录")
    extraction_method: str = Field(default="source_snippet", description="抽取方法")


class ClaimRecord(BaseModel):
    """单条 claim 记录。"""

    claim_id: str = Field(description="claim ID")
    text: str = Field(description="claim 文本")
    criticality: str = Field(default="medium", description="low / medium / high")
    uncertainty: str = Field(default="medium", description="low / medium / high")
    status: str = Field(default="unverifiable", description="claim 支撑状态")
    placeholder: bool = Field(default=False, description="是否为占位 claim")
    section_ref: str = Field(default="", description="对应报告章节或任务标题")
    evidence_ids: list[str] = Field(default_factory=list, description="关联证据片段 ID")


class ClaimSupportEdgeRecord(BaseModel):
    """Claim 与证据之间的边。"""

    edge_id: str = Field(description="边 ID")
    claim_id: str = Field(description="claim ID")
    evidence_id: str = Field(description="证据 ID")
    relation: str = Field(description="supports / partially_supports / contradicts / context_only")
    confidence: float = Field(default=0.0, description="边置信度")
    notes: str = Field(default="", description="判定说明")


class ConflictSetRecord(BaseModel):
    """冲突集合。"""

    conflict_id: str = Field(description="冲突集合 ID")
    claim_ids: list[str] = Field(default_factory=list, description="涉及的 claims")
    evidence_ids: list[str] = Field(default_factory=list, description="涉及的 evidence")
    status: str = Field(default="open", description="open / reviewed / resolved")
    summary: str = Field(default="", description="冲突摘要")


class CriticalClaimReviewItem(BaseModel):
    """关键 claim 复核队列条目。"""

    review_id: str = Field(description="复核条目 ID")
    claim_id: str = Field(description="claim ID")
    text: str = Field(description="claim 文本")
    status: str = Field(default="blocked", description="blocked / queued / resolved")
    reason: str = Field(default="", description="阻塞原因")
    blocking: bool = Field(default=True, description="是否阻塞交付")
    evidence_ids: list[str] = Field(default_factory=list, description="关联证据")
    edge_ids: list[str] = Field(default_factory=list, description="关联边")
    notes: str = Field(default="", description="补充说明")


class ClaimReviewQueue(BaseModel):
    """关键 claim 复核队列文件。"""

    job_id: str = Field(description="job ID")
    created_at: str = Field(default_factory=utc_now_iso, description="创建时间")
    items: list[CriticalClaimReviewItem] = Field(default_factory=list, description="复核条目")


class AuditDecision(BaseModel):
    """审计门禁判定结果。"""

    gate_status: str = Field(default="passed", description="passed / blocked")
    critical_claim_count: int = Field(default=0, description="关键 claim 数")
    blocked_critical_claim_count: int = Field(default=0, description="被阻塞的关键 claim 数")
    block_reason: str = Field(default="", description="阻塞摘要")
