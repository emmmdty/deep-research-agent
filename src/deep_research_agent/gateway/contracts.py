"""Public request/response contracts for the Phase 4 gateway surfaces."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from deep_research_agent.research_jobs.models import JobRuntimeRecord, JobProgressEvent


ReviewDecision = Literal["approve", "downgrade", "reject", "override"]


class StrictModel(BaseModel):
    """Base model for public contracts that reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


class SubmitJobRequest(StrictModel):
    """Public request for creating one research job."""

    topic: str = Field(min_length=1, description="Research topic or brief.")
    max_loops: int = Field(default=3, ge=1, description="Maximum research loop count.")
    research_profile: str = Field(default="default", min_length=1)
    source_profile: str = Field(default="company_broad", min_length=1)
    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)
    connector_budget: dict[str, int] | None = Field(default=None)
    start_worker: bool = Field(default=True)


class RetryJobRequest(StrictModel):
    """Public request for retrying a job as a new attempt."""

    start_worker: bool = Field(default=True)


class ResumeJobRequest(StrictModel):
    """Public request for resuming the same job from its latest checkpoint."""

    start_worker: bool = Field(default=True)


class RefineJobRequest(StrictModel):
    """Public request for recording a refinement instruction."""

    instruction: str = Field(min_length=1)
    start_worker: bool = Field(default=True)


class ReviewJobRequest(StrictModel):
    """Public request for recording a human review action."""

    review_item_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    decision: ReviewDecision
    reason: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)


class EmptyRequest(StrictModel):
    """Placeholder model for body-less control-plane calls."""


class PublicJobResponse(StrictModel):
    """Stable public projection for a research job."""

    job_id: str
    topic: str
    status: str
    current_stage: str
    created_at: str
    updated_at: str
    attempt_index: int
    retry_of: str | None = None
    cancel_requested: bool
    source_profile: str
    budget: dict[str, Any] = Field(default_factory=dict)
    policy_overrides: dict[str, Any] = Field(default_factory=dict)
    connector_health: dict[str, Any] = Field(default_factory=dict)
    audit_gate_status: str
    critical_claim_count: int
    blocked_critical_claim_count: int
    error: str | None = None
    artifact_urls: dict[str, str] = Field(default_factory=dict)


class PublicJobEvent(StrictModel):
    """Stable public projection for one job event."""

    event_id: str
    job_id: str
    sequence: int
    stage: str
    event_type: str
    timestamp: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class JobEventsResponse(StrictModel):
    """Public response for an ordered event stream slice."""

    job_id: str
    events: list[PublicJobEvent] = Field(default_factory=list)


class BatchResearchRequest(StrictModel):
    """Public request for submitting many jobs with the same contract."""

    jobs: list[SubmitJobRequest] = Field(min_length=1)


class BatchResearchResponse(StrictModel):
    """Public response for batch job creation."""

    accepted_count: int = Field(ge=0)
    jobs: list[PublicJobResponse] = Field(default_factory=list)


def build_artifact_urls(job_id: str) -> dict[str, str]:
    """Build stable public URLs without leaking local filesystem paths."""

    base = f"/v1/research/jobs/{job_id}"
    return {
        "self": base,
        "events": f"{base}/events",
        "bundle": f"{base}/bundle",
        "report_markdown": f"{base}/artifacts/report.md",
        "report_html": f"{base}/artifacts/report.html",
        "report_bundle": f"{base}/artifacts/report_bundle.json",
        "claims": f"{base}/artifacts/claims.json",
        "sources": f"{base}/artifacts/sources.json",
        "audit_decision": f"{base}/artifacts/audit_decision.json",
        "trace": f"{base}/artifacts/trace.jsonl",
        "manifest": f"{base}/artifacts/manifest.json",
        "review_queue": f"{base}/artifacts/review_queue.json",
        "claim_graph": f"{base}/artifacts/claim_graph.json",
        "review_actions": f"{base}/artifacts/review_actions.jsonl",
    }


def public_job_response(job: JobRuntimeRecord) -> PublicJobResponse:
    """Project an internal job record into the stable public contract."""

    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    current_stage = job.current_stage.value if hasattr(job.current_stage, "value") else str(job.current_stage)
    audit_gate_status = (
        job.audit_gate_status.value if hasattr(job.audit_gate_status, "value") else str(job.audit_gate_status)
    )
    return PublicJobResponse(
        job_id=job.job_id,
        topic=job.topic,
        status=status,
        current_stage=current_stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        attempt_index=job.attempt_index,
        retry_of=job.retry_of,
        cancel_requested=job.cancel_requested,
        source_profile=job.source_profile,
        budget=dict(job.budget),
        policy_overrides=dict(job.policy_overrides),
        connector_health=dict(job.connector_health),
        audit_gate_status=audit_gate_status,
        critical_claim_count=job.critical_claim_count,
        blocked_critical_claim_count=job.blocked_critical_claim_count,
        error=job.error,
        artifact_urls=build_artifact_urls(job.job_id),
    )


def public_job_event(event: JobProgressEvent) -> PublicJobEvent:
    """Project an internal event record into the stable public contract."""

    return PublicJobEvent(
        event_id=event.event_id,
        job_id=event.job_id,
        sequence=event.sequence,
        stage=event.stage,
        event_type=event.event_type,
        timestamp=event.timestamp,
        message=event.message,
        payload=dict(event.payload),
    )
