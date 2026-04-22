"""Contracts for external benchmark adapters and manifests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BENCHMARK_NAMES = ("facts_grounding", "longfact_safe", "longbench_v2", "browsecomp", "gaia")
BENCHMARK_ROLES = (
    "authoritative_release_gate",
    "secondary_regression",
    "external_regression",
    "challenge_track",
)
ADAPTER_MODES = (
    "domain_report_bundle",
    "facts_doc_grounded_longform",
    "longfact_safe_open_domain_longform",
    "longbench_mcq_longcontext",
    "browsecomp_short_answer",
    "gaia_capability_gated",
)
BENCHMARK_STATUSES = ("completed", "blocked", "failed")


class BenchmarkRunRequest(BaseModel):
    """Runtime request for one external benchmark invocation."""

    benchmark_name: Literal["facts_grounding", "longfact_safe", "longbench_v2", "browsecomp", "gaia"]
    output_root: str
    split: str | None = None
    subset: str | None = None
    bucket: str | None = None
    config_path: str | None = None


class BenchmarkTaskSpec(BaseModel):
    """Task fixture or normalized benchmark task."""

    task_id: str
    prompt: str
    expected_answer: str | None = None
    prediction: str | None = None
    eligible: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)


class BenchmarkTaskResult(BaseModel):
    """Normalized per-task benchmark result row."""

    benchmark: Literal["facts_grounding", "longfact_safe", "longbench_v2", "browsecomp", "gaia"]
    task_id: str
    status: Literal["completed", "blocked", "failed"]
    prompt: str
    prediction: str | None = None
    expected_answer: str | None = None
    official_metrics: dict[str, object] = Field(default_factory=dict)
    internal_metrics: dict[str, object] = Field(default_factory=dict)
    blocked_reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class BenchmarkIntegrityReport(BaseModel):
    """Benchmark-specific integrity report sidecar."""

    benchmark: Literal["facts_grounding", "longfact_safe", "longbench_v2", "browsecomp", "gaia"]
    status: Literal["not_applicable", "passed", "blocked", "failed"] = "not_applicable"
    guards: list[str] = Field(default_factory=list)
    findings: list[dict[str, object]] = Field(default_factory=list)
    summary: str = ""


class BenchmarkRunManifest(BaseModel):
    """Top-level artifact index for one benchmark run."""

    benchmark: Literal["facts_grounding", "longfact_safe", "longbench_v2", "browsecomp", "gaia"]
    title: str
    adapter_mode: Literal[
        "domain_report_bundle",
        "facts_doc_grounded_longform",
        "longfact_safe_open_domain_longform",
        "longbench_mcq_longcontext",
        "browsecomp_short_answer",
        "gaia_capability_gated",
    ]
    role: Literal[
        "authoritative_release_gate",
        "secondary_regression",
        "external_regression",
        "challenge_track",
    ]
    status: Literal["completed", "blocked", "failed"]
    split: str | None = None
    subset: str | None = None
    bucket: str | None = None
    started_at: str
    completed_at: str
    output_root: str
    config_path: str | None = None
    dataset_manifest_path: str | None = None
    task_count: int
    completed_count: int
    blocked_count: int = 0
    failed_count: int = 0
    official_metrics: dict[str, object] = Field(default_factory=dict)
    internal_metrics: dict[str, object] = Field(default_factory=dict)
    integrity_report: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    search_backend: str | None = None
    judge_backend: str | None = None
    integrity_guards: list[str] = Field(default_factory=list)
    environment: dict[str, object] = Field(default_factory=dict)


class BenchmarkPortfolioSummary(BaseModel):
    """Reviewer-facing summary for the full benchmark portfolio."""

    generated_at: str
    authoritative_release_gate: list[str] = Field(default_factory=list)
    secondary_regression: list[str] = Field(default_factory=list)
    external_regression: list[str] = Field(default_factory=list)
    challenge_track: list[str] = Field(default_factory=list)
    deferred: list[str] = Field(default_factory=list)
    runs: list[dict[str, object]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
