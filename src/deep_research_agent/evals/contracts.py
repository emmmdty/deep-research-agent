"""Contracts for Phase 05 local eval suites."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EVAL_SUITE_NAMES = ("company12", "industry12", "trusted8", "file8", "recovery6")


class EvalThreshold(BaseModel):
    """Threshold for one aggregate eval metric."""

    min: float | None = None
    max: float | None = None


class EvalSourceSpec(BaseModel):
    """Frozen public source fixture for a local eval task."""

    citation_id: int = Field(default=0)
    source_id: str = Field(default="")
    source_type: str = Field(default="web")
    query: str = Field(default="")
    title: str
    canonical_uri: str
    url: str = Field(default="")
    snippet: str = Field(default="")
    snapshot_ref: str = Field(default="")
    trust_tier: int = Field(default=3)
    auth_scope: str = Field(default="public")
    mime_type: str = Field(default="text/plain")
    freshness_metadata: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    selected: bool = Field(default=True)


class EvalEvidenceSpec(BaseModel):
    """Frozen evidence-fragment fixture."""

    evidence_id: str
    source_id: str
    snapshot_id: str
    excerpt: str
    locator: dict[str, object] = Field(default_factory=dict)
    extraction_method: str = Field(default="fixture")


class EvalClaimSpec(BaseModel):
    """Frozen claim fixture."""

    claim_id: str
    text: str
    criticality: str = Field(default="high")
    uncertainty: str = Field(default="low")
    status: str = Field(default="supported")
    placeholder: bool = Field(default=False)
    section_ref: str = Field(default="")
    evidence_ids: list[str] = Field(default_factory=list)


class EvalEdgeSpec(BaseModel):
    """Frozen claim-support edge fixture."""

    edge_id: str
    claim_id: str
    evidence_id: str
    source_id: str = Field(default="")
    snapshot_id: str = Field(default="")
    locator: dict[str, object] = Field(default_factory=dict)
    relation: str = Field(default="supports")
    confidence: float = Field(default=1.0)
    grounding_status: str = Field(default="grounded")
    notes: str = Field(default="")


class EvalConflictSpec(BaseModel):
    """Frozen conflict-set fixture."""

    conflict_id: str
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = Field(default="reviewed")
    summary: str = Field(default="")


class EvalTaskSpec(BaseModel):
    """One deterministic local eval task."""

    task_id: str
    topic: str
    source_profile: str
    research_profile: str = Field(default="eval_smoke")
    required_questions: list[str] = Field(default_factory=list)
    answered_questions: list[str] = Field(default_factory=list)
    report_markdown: str
    task_summaries: list[str] = Field(default_factory=list)
    sources: list[EvalSourceSpec] = Field(default_factory=list)
    evidence_fragments: list[EvalEvidenceSpec] = Field(default_factory=list)
    claims: list[EvalClaimSpec] = Field(default_factory=list)
    claim_support_edges: list[EvalEdgeSpec] = Field(default_factory=list)
    conflict_sets: list[EvalConflictSpec] = Field(default_factory=list)
    file_inputs: list[str] = Field(default_factory=list)
    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)


class EvalDataset(BaseModel):
    """Dataset payload for a suite."""

    variant: str = Field(default="smoke_local")
    tasks: list[EvalTaskSpec] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list)


class EvalSuiteDefinition(BaseModel):
    """Top-level suite metadata."""

    suite_name: Literal["company12", "industry12", "trusted8", "file8", "recovery6"]
    executor: Literal["research_fixture", "reliability_fixture"]
    description: str
    dataset_path: str | None = None
    rubric_path: str | None = None
    thresholds: dict[str, EvalThreshold] = Field(default_factory=dict)
