"""Domain-agnostic contracts for the V2 research runtime."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Sha256Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
TaskDependencyRef = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class StrictModel(BaseModel):
    """Boundary model that rejects fields outside its declared contract."""

    model_config = ConfigDict(extra="forbid")


class ResearchBrief(StrictModel):
    """Structured research request compiled from a user conversation."""

    brief_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    domain_pack_id: str = Field(min_length=1)
    objectives: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ArtifactRef(StrictModel):
    """Immutable reference to a task-produced artifact."""

    artifact_id: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    content_sha256: str = Field(min_length=1)
    created_by_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskSpec(StrictModel):
    """One durable task in a compiled research DAG."""

    task_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    role: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    depends_on: list[TaskDependencyRef] = Field(default_factory=list)
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    output_schema: dict[str, Any]
    budget: dict[str, int | float] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_dependencies(self) -> TaskSpec:
        if self.task_id in self.depends_on:
            raise ValueError("a task cannot depend on itself")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("task dependencies must be unique")
        return self


class EvidenceSpan(StrictModel):
    """Exact excerpt from an immutable document version."""

    span_id: str = Field(min_length=1)
    document_version_id: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    quote: str = Field(min_length=1)
    extraction_method: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_offsets(self) -> EvidenceSpan:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("evidence offsets must be provided together")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset <= self.start_offset
        ):
            raise ValueError("evidence end_offset must be greater than start_offset")
        if self.page is None and not self.section and self.start_offset is None:
            raise ValueError("evidence requires a page, section, or offset locator")
        return self


class ClaimRecord(StrictModel):
    """Auditable research claim and the evidence used to classify it."""

    claim_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    claim_type: str = Field(min_length=1)
    critical: bool = False
    support_status: Literal["accepted", "qualified", "contradicted", "unsupported"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_evidence_for_critical_accepted_claim(self) -> ClaimRecord:
        if self.critical and self.support_status == "accepted" and not self.evidence_spans:
            raise ValueError("critical accepted claims require evidence spans")
        return self


class EvidencePacket(StrictModel):
    """Typed evidence emitted by one research task."""

    packet_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    claims: list[ClaimRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class TaskResult(StrictModel):
    """Validated completion envelope for one research task."""

    task_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    status: Literal["completed", "failed", "cancelled"]
    evidence_packets: list[EvidencePacket] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    error: str | None = None


class ResearchGraphNode(StrictModel):
    """Domain-neutral node in a research relationship graph."""

    node_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    label: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)


class ResearchGraphEdge(StrictModel):
    """Domain-neutral relation whose semantics come from a domain pack."""

    edge_id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    evidence_span_ids: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class ResearchGraph(StrictModel):
    """Generic graph carried by a report bundle."""

    nodes: list[ResearchGraphNode] = Field(default_factory=list)
    edges: list[ResearchGraphEdge] = Field(default_factory=list)


class CorpusManifest(StrictModel):
    """Frozen set of immutable document versions used by one run."""

    manifest_id: str = Field(min_length=1)
    document_version_ids: list[str] = Field(default_factory=list)
    content_hashes: dict[str, Sha256Digest] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_document_hashes(self) -> CorpusManifest:
        missing_hashes = set(self.document_version_ids) - self.content_hashes.keys()
        if missing_hashes:
            missing = ", ".join(sorted(missing_hashes))
            raise ValueError(f"content hash required for document versions: {missing}")
        return self


class ReportBundleV2(StrictModel):
    """Versioned, reproducible output of the V2 research runtime."""

    schema_version: Literal["2.0"] = "2.0"
    report_markdown: str
    accepted_claims: list[ClaimRecord]
    qualified_claims: list[ClaimRecord]
    evidence_matrix: dict[str, list[str]]
    research_graph: ResearchGraph
    sources: list[ArtifactRef]
    audit_summary: dict[str, Any]
    corpus_manifest: CorpusManifest
    run_manifest: dict[str, Any]

    @model_validator(mode="after")
    def _validate_claim_buckets(self) -> ReportBundleV2:
        expected_status_by_bucket = {
            "accepted_claims": "accepted",
            "qualified_claims": "qualified",
        }
        for bucket, expected_status in expected_status_by_bucket.items():
            claims = getattr(self, bucket)
            if any(claim.support_status != expected_status for claim in claims):
                raise ValueError(f"{bucket} must contain only {expected_status} claims")

        manifest_document_ids = set(self.corpus_manifest.document_version_ids)
        claim_document_ids = {
            span.document_version_id
            for claim in (*self.accepted_claims, *self.qualified_claims)
            for span in claim.evidence_spans
        }
        matrix_document_ids = {
            document_version_id
            for document_version_ids in self.evidence_matrix.values()
            for document_version_id in document_version_ids
        }
        unfrozen_document_ids = (
            claim_document_ids | matrix_document_ids
        ) - manifest_document_ids
        if unfrozen_document_ids:
            unfrozen = ", ".join(sorted(unfrozen_document_ids))
            raise ValueError(f"document version references are outside the frozen corpus: {unfrozen}")
        return self
