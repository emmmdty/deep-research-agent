"""Canonical Phase 02 runtime contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from deep_research_agent.common import DEFAULT_SOURCE_PROFILE, resolve_source_profile_name


class JobStatus(str, Enum):
    """Lifecycle status for a research job."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RuntimeStage(str, Enum):
    """Deterministic stage pointer for the runtime control plane."""

    CREATED = "created"
    CLARIFYING = "clarifying"
    PLANNED = "planned"
    COLLECTING = "collecting"
    NORMALIZING = "normalizing"
    EXTRACTING = "extracting"
    CLAIM_AUDITING = "claim_auditing"
    SYNTHESIZING = "synthesizing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditGateStatus(str, Enum):
    """Audit-gate status is intentionally separate from lifecycle status."""

    UNCHECKED = "unchecked"
    PASSED = "passed"
    BLOCKED = "blocked"
    PENDING_MANUAL_REVIEW = "pending_manual_review"


ACTIVE_JOB_STATUSES = frozenset({JobStatus.CREATED.value, JobStatus.RUNNING.value})
TERMINAL_JOB_STATUSES = frozenset(
    {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}
)
RUNTIME_STAGE_ORDER = (
    RuntimeStage.CREATED,
    RuntimeStage.CLARIFYING,
    RuntimeStage.PLANNED,
    RuntimeStage.COLLECTING,
    RuntimeStage.NORMALIZING,
    RuntimeStage.EXTRACTING,
    RuntimeStage.CLAIM_AUDITING,
    RuntimeStage.SYNTHESIZING,
    RuntimeStage.RENDERING,
    RuntimeStage.COMPLETED,
)
REFINEMENT_SAFE_STAGE = RuntimeStage.PLANNED


def utc_now_iso() -> str:
    """返回 UTC ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


class JobRuntimeRecord(BaseModel):
    """Canonical runtime projection for a research job."""

    job_id: str = Field(description="job 唯一标识")
    topic: str = Field(description="原始研究主题")
    status: JobStatus = Field(description="job 生命周期状态")
    current_stage: RuntimeStage = Field(description="当前即将执行的阶段")
    created_at: str = Field(default_factory=utc_now_iso, description="创建时间")
    updated_at: str = Field(default_factory=utc_now_iso, description="更新时间")
    attempt_index: int = Field(default=1, description="重试序号")
    retry_of: str | None = Field(default=None, description="上一次 job_id")
    cancel_requested: bool = Field(default=False, description="是否请求取消")
    worker_pid: int | None = Field(default=None, description="当前 worker pid")
    worker_lease_id: str | None = Field(default=None, description="当前 worker lease")
    last_heartbeat_at: str | None = Field(default=None, description="最近心跳时间")
    active_checkpoint_id: str | None = Field(default=None, description="最新稳定 checkpoint")
    report_path: str = Field(description="最终 Markdown 路径")
    report_bundle_path: str = Field(description="最终 bundle 路径")
    trace_path: str = Field(description="最终 trace 路径")
    runtime_path: str = Field(default="orchestrator-v1", description="运行时实现标识")
    source_profile: str = Field(default=DEFAULT_SOURCE_PROFILE, description="来源策略 profile")
    budget: dict[str, Any] = Field(default_factory=dict, description="connector 预算")
    policy_overrides: dict[str, Any] = Field(default_factory=dict, description="策略覆盖")
    connector_health: dict[str, Any] = Field(default_factory=dict, description="connector 健康状态")
    audit_gate_status: AuditGateStatus = Field(
        default=AuditGateStatus.UNCHECKED,
        description="审计门禁状态",
    )
    critical_claim_count: int = Field(default=0, description="关键 claim 数")
    blocked_critical_claim_count: int = Field(default=0, description="阻塞中的关键 claim 数")
    audit_graph_path: str = Field(default="", description="claim graph 文件路径")
    review_queue_path: str = Field(default="", description="review queue 文件路径")
    error: str | None = Field(default=None, description="错误信息")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    @field_validator("source_profile", mode="before")
    @classmethod
    def _normalize_source_profile(cls, value: str | None) -> str:
        return resolve_source_profile_name(value)


class JobProgressEvent(BaseModel):
    """job 进度事件。"""

    event_id: str = Field(description="事件 ID")
    job_id: str = Field(description="job ID")
    sequence: int = Field(description="事件序号")
    stage: str = Field(description="所属阶段")
    event_type: str = Field(description="事件类型")
    timestamp: str = Field(default_factory=utc_now_iso, description="事件时间")
    message: str = Field(default="", description="用户可读说明")
    payload: dict[str, Any] = Field(default_factory=dict, description="扩展载荷")


class JobCheckpoint(BaseModel):
    """可恢复 checkpoint。"""

    checkpoint_id: str = Field(description="checkpoint ID")
    job_id: str = Field(description="job ID")
    stage: RuntimeStage = Field(description="已完成阶段")
    sequence: int = Field(description="checkpoint 序号")
    loop_count: int = Field(default=0, description="当前 loop 次数")
    created_at: str = Field(default_factory=utc_now_iso, description="创建时间")
    next_stage: RuntimeStage = Field(description="恢复后应继续执行的阶段")
    state_payload: dict[str, Any] = Field(default_factory=dict, description="ResearchState payload")
