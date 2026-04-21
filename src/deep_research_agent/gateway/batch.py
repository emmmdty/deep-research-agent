"""Shared batch helpers for CLI and API surfaces."""

from __future__ import annotations

import json
from pathlib import Path

from deep_research_agent.gateway.contracts import BatchResearchResponse, SubmitJobRequest, public_job_response
from deep_research_agent.research_jobs import ResearchJobService


def load_batch_requests(path: str | Path) -> list[SubmitJobRequest]:
    """Load a batch file as JSON array or JSONL."""

    batch_path = Path(path)
    content = batch_path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    if content.startswith("["):
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise ValueError("batch JSON file must be a list")
        return [SubmitJobRequest.model_validate(item) for item in payload]
    return [
        SubmitJobRequest.model_validate(json.loads(line))
        for line in content.splitlines()
        if line.strip()
    ]


def submit_batch_jobs(service: ResearchJobService, requests: list[SubmitJobRequest]) -> BatchResearchResponse:
    """Submit a batch of jobs through the canonical research job service."""

    jobs = [
        public_job_response(
            service.submit(
                topic=item.topic,
                max_loops=item.max_loops,
                research_profile=item.research_profile,
                start_worker=item.start_worker,
                source_profile=item.source_profile,
                allow_domains=item.allow_domains,
                deny_domains=item.deny_domains,
                connector_budget=item.connector_budget,
            )
        )
        for item in requests
    ]
    return BatchResearchResponse(accepted_count=len(jobs), jobs=jobs)
