"""Helpers for serving stable job artifact names without exposing local paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deep_research_agent.research_jobs.models import JobRuntimeRecord


ARTIFACT_NAME_CHOICES = (
    "report.md",
    "report.html",
    "report_bundle.json",
    "claims.json",
    "sources.json",
    "audit_decision.json",
    "trace.jsonl",
    "manifest.json",
    "review_queue.json",
    "claim_graph.json",
    "review_actions.jsonl",
)


def artifact_path_for_job(job: JobRuntimeRecord, artifact_name: str) -> Path:
    """Resolve one stable artifact name to the current local file path."""

    bundle_dir = Path(job.report_bundle_path).parent
    if artifact_name == "report.md":
        return Path(job.report_path)
    if artifact_name == "report.html":
        return bundle_dir / "report.html"
    if artifact_name == "report_bundle.json":
        return Path(job.report_bundle_path)
    if artifact_name == "claims.json":
        return bundle_dir / "claims.json"
    if artifact_name == "sources.json":
        return bundle_dir / "sources.json"
    if artifact_name == "audit_decision.json":
        return bundle_dir / "audit_decision.json"
    if artifact_name == "trace.jsonl":
        return Path(job.trace_path)
    if artifact_name == "manifest.json":
        return bundle_dir / "manifest.json"
    if artifact_name == "review_queue.json":
        return Path(job.review_queue_path)
    if artifact_name == "claim_graph.json":
        return Path(job.audit_graph_path)
    if artifact_name == "review_actions.jsonl":
        return Path(job.review_queue_path).parent / "review_actions.jsonl"
    raise KeyError(f"unsupported artifact: {artifact_name}")


def load_json_artifact(path: Path) -> Any:
    """Load one JSON artifact from disk."""

    return json.loads(path.read_text(encoding="utf-8"))
