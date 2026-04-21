"""Phase 4 public surface contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def _write_job_artifacts(job) -> None:
    bundle_dir = Path(job.report_bundle_path).parent
    audit_dir = Path(job.review_queue_path).parent
    bundle_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    Path(job.report_path).write_text("# Report\n\nSurface smoke.\n", encoding="utf-8")
    Path(job.report_bundle_path).write_text(
        json.dumps(
            {
                "job": {"job_id": job.job_id, "status": job.status, "runtime_path": "orchestrator-v1"},
                "report_text": "Surface smoke.",
                "audit_summary": {"gate_status": job.audit_gate_status},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "job": {"job_id": job.job_id},
                "artifacts": {
                    "report_bundle": "bundle/report_bundle.json",
                    "report_html": "bundle/report.html",
                    "report_markdown": "report.md",
                    "trace": "bundle/trace.jsonl",
                    "review_queue": "audit/review_queue.json",
                    "claim_graph": "audit/claim_graph.json",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "report.html").write_text("<html><body>Surface smoke.</body></html>", encoding="utf-8")
    (bundle_dir / "claims.json").write_text(json.dumps({"claims": []}, ensure_ascii=False), encoding="utf-8")
    (bundle_dir / "sources.json").write_text(
        json.dumps({"citations": [], "sources": [], "snapshots": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (bundle_dir / "audit_decision.json").write_text(
        json.dumps({"gate_status": job.audit_gate_status, "blocking_claim_ids": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    Path(job.trace_path).write_text(
        json.dumps({"sequence": 1, "event_type": "job.created"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    Path(job.review_queue_path).write_text(json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8")
    Path(job.audit_graph_path).write_text(
        json.dumps({"claims": [], "claim_support_edges": [], "conflict_sets": []}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_http_api_submit_status_events_bundle_and_artifacts(tmp_path: Path):
    """API 应暴露 submit/status/events/bundle/artifact 基本闭环。"""
    from fastapi.testclient import TestClient

    from deep_research_agent.gateway.api import create_app
    from deep_research_agent.research_jobs import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    app = create_app(service_factory=lambda: service)
    client = TestClient(app)

    submit_payload = {
        "topic": "Phase 4 API smoke",
        "max_loops": 2,
        "research_profile": "default",
        "source_profile": "company_trusted",
        "allow_domains": ["docs.langchain.com"],
        "deny_domains": ["reddit.com"],
        "connector_budget": {"max_fetches_per_task": 2},
        "start_worker": False,
    }
    response = client.post("/v1/research/jobs", json=submit_payload)
    assert response.status_code == 202

    job = response.json()
    job_id = job["job_id"]

    status_response = client.get(f"/v1/research/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["job_id"] == job_id
    assert status_response.json()["artifact_urls"]["bundle"].endswith(f"/v1/research/jobs/{job_id}/bundle")

    events_response = client.get(f"/v1/research/jobs/{job_id}/events")
    assert events_response.status_code == 200
    payload = events_response.json()
    assert payload["job_id"] == job_id
    assert payload["events"][0]["event_type"] == "job.created"

    stored = service.get(job_id)
    assert stored is not None
    completed = service.store.update_job(
        job_id,
        status="completed",
        current_stage="completed",
        audit_gate_status="passed",
    )
    _write_job_artifacts(completed)

    bundle_response = client.get(f"/v1/research/jobs/{job_id}/bundle")
    assert bundle_response.status_code == 200
    assert bundle_response.json()["job"]["job_id"] == job_id

    artifact_response = client.get(f"/v1/research/jobs/{job_id}/artifacts/report.html")
    assert artifact_response.status_code == 200
    assert "Surface smoke." in artifact_response.text


def test_http_api_lifecycle_and_review_routes(tmp_path: Path):
    """API 应复用 cancel/retry/resume/refine/review 生命周期语义。"""
    from fastapi.testclient import TestClient

    from deep_research_agent.gateway.api import create_app
    from deep_research_agent.research_jobs import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    app = create_app(service_factory=lambda: service)
    client = TestClient(app)

    created = client.post(
        "/v1/research/jobs",
        json={
            "topic": "Phase 4 lifecycle",
            "max_loops": 1,
            "research_profile": "default",
            "start_worker": False,
        },
    ).json()
    job_id = created["job_id"]

    cancel_response = client.post(f"/v1/research/jobs/{job_id}:cancel", json={})
    assert cancel_response.status_code == 200
    assert cancel_response.json()["cancel_requested"] is True

    service.store.update_job(job_id, status="failed", current_stage="failed", error="smoke failure")

    retry_response = client.post(f"/v1/research/jobs/{job_id}:retry", json={"start_worker": False})
    assert retry_response.status_code == 200
    assert retry_response.json()["retry_of"] == job_id

    resume_response = client.post(f"/v1/research/jobs/{job_id}:resume", json={"start_worker": False})
    assert resume_response.status_code == 200
    assert resume_response.json()["job_id"] == job_id

    refine_response = client.post(
        f"/v1/research/jobs/{job_id}:refine",
        json={"instruction": "Expand the evidence table.", "start_worker": False},
    )
    assert refine_response.status_code == 200
    assert refine_response.json()["current_stage"] == "planned"

    review_response = client.post(
        f"/v1/research/jobs/{job_id}:review",
        json={
            "review_item_id": "review-1",
            "claim_id": "claim-1",
            "decision": "override",
            "reason": "Human reviewer accepted the claim after manual verification.",
            "reviewer": "phase4-test",
        },
    )
    assert review_response.status_code == 200
    assert review_response.json()["audit_gate_status"] in {"passed", "pending_manual_review", "blocked"}


def test_http_api_batch_route_and_public_contract_schemas(tmp_path: Path):
    """batch API 与 public contract schema 都应可验证。"""
    from fastapi.testclient import TestClient

    from deep_research_agent.gateway.api import create_app
    from deep_research_agent.gateway.contracts import (
        BatchResearchRequest,
        BatchResearchResponse,
        JobEventsResponse,
        PublicJobResponse,
        ReviewJobRequest,
        SubmitJobRequest,
    )
    from deep_research_agent.research_jobs import ResearchJobService

    submit_example = {
        "topic": "Phase 4 schema smoke",
        "max_loops": 1,
        "research_profile": "default",
        "source_profile": "company_broad",
        "start_worker": False,
    }
    review_example = {
        "review_item_id": "review-1",
        "claim_id": "claim-1",
        "decision": "approve",
        "reason": "Grounded after review.",
        "reviewer": "tester",
    }
    events_example = {
        "job_id": "job-1",
        "events": [
            {
                "event_id": "job-1-event-0001",
                "job_id": "job-1",
                "sequence": 1,
                "stage": "job",
                "event_type": "job.created",
                "timestamp": "2026-04-21T00:00:00+00:00",
                "message": "created",
                "payload": {},
            }
        ],
    }

    for model, instance in (
        (SubmitJobRequest, submit_example),
        (ReviewJobRequest, review_example),
        (JobEventsResponse, events_example),
    ):
        schema = model.model_json_schema()
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)

    service = ResearchJobService(workspace_dir=str(tmp_path))
    app = create_app(service_factory=lambda: service)
    client = TestClient(app)

    batch_payload = {
        "jobs": [
            submit_example,
            {
                "topic": "Phase 4 schema smoke 2",
                "max_loops": 2,
                "research_profile": "benchmark",
                "source_profile": "industry_trusted",
                "start_worker": False,
            },
        ]
    }
    batch_response = client.post("/v1/batch/research", json=batch_payload)
    assert batch_response.status_code == 202

    body = batch_response.json()
    assert body["accepted_count"] == 2
    assert len(body["jobs"]) == 2

    for model, instance in (
        (BatchResearchRequest, batch_payload),
        (BatchResearchResponse, body),
        (PublicJobResponse, body["jobs"][0]),
    ):
        schema = model.model_json_schema()
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
