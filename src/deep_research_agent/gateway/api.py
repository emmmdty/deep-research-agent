"""FastAPI surface for the deterministic research job runtime."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from deep_research_agent.gateway.artifacts import ARTIFACT_NAME_CHOICES, artifact_path_for_job, load_json_artifact
from deep_research_agent.gateway.batch import submit_batch_jobs
from deep_research_agent.gateway.contracts import (
    BatchResearchRequest,
    BatchResearchResponse,
    EmptyRequest,
    JobEventsResponse,
    PublicJobResponse,
    RefineJobRequest,
    ResumeJobRequest,
    RetryJobRequest,
    ReviewJobRequest,
    SubmitJobRequest,
    public_job_event,
    public_job_response,
)
from deep_research_agent.research_jobs import ResearchJobService


ServiceFactory = Callable[[], ResearchJobService]


def create_app(*, service_factory: ServiceFactory | None = None) -> FastAPI:
    """Create the local Phase 4 HTTP API."""

    factory = service_factory or ResearchJobService
    app = FastAPI(
        title="Deep Research Agent API",
        version="0.1.0",
        summary="Deterministic HTTP surface for async research jobs and report bundles.",
    )

    def get_service() -> ResearchJobService:
        return factory()

    def require_job(service: ResearchJobService, job_id: str):
        job = service.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
        return job

    def _conflict(error: Exception) -> HTTPException:
        return HTTPException(status_code=409, detail=str(error))

    @app.post("/v1/research/jobs", response_model=PublicJobResponse, status_code=202)
    def submit_research_job(
        request: SubmitJobRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        job = service.submit(
            topic=request.topic,
            max_loops=request.max_loops,
            research_profile=request.research_profile,
            start_worker=request.start_worker,
            source_profile=request.source_profile,
            allow_domains=request.allow_domains,
            deny_domains=request.deny_domains,
            connector_budget=request.connector_budget,
        )
        return public_job_response(job)

    @app.get("/v1/research/jobs/{job_id}", response_model=PublicJobResponse)
    def get_research_job(
        job_id: str,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        return public_job_response(require_job(service, job_id))

    @app.get("/v1/research/jobs/{job_id}/events", response_model=JobEventsResponse)
    def get_research_job_events(
        job_id: str,
        after_sequence: int = Query(default=0, ge=0),
        service: ResearchJobService = Depends(get_service),
    ) -> JobEventsResponse:
        require_job(service, job_id)
        events = [public_job_event(item) for item in service.list_events(job_id, after_sequence=after_sequence)]
        return JobEventsResponse(job_id=job_id, events=events)

    @app.post("/v1/research/jobs/{job_id}:cancel", response_model=PublicJobResponse)
    def cancel_research_job(
        job_id: str,
        _: EmptyRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        try:
            return public_job_response(service.cancel(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/research/jobs/{job_id}:retry", response_model=PublicJobResponse)
    def retry_research_job(
        job_id: str,
        request: RetryJobRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        try:
            return public_job_response(service.retry(job_id, start_worker=request.start_worker))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise _conflict(exc) from exc

    @app.post("/v1/research/jobs/{job_id}:resume", response_model=PublicJobResponse)
    def resume_research_job(
        job_id: str,
        request: ResumeJobRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        try:
            return public_job_response(service.resume(job_id, start_worker=request.start_worker))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise _conflict(exc) from exc

    @app.post("/v1/research/jobs/{job_id}:refine", response_model=PublicJobResponse)
    def refine_research_job(
        job_id: str,
        request: RefineJobRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        try:
            return public_job_response(
                service.refine(
                    job_id,
                    request.instruction,
                    start_worker=request.start_worker,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise _conflict(exc) from exc

    @app.post("/v1/research/jobs/{job_id}:review", response_model=PublicJobResponse)
    def review_research_job(
        job_id: str,
        request: ReviewJobRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> PublicJobResponse:
        try:
            return public_job_response(
                service.record_review(
                    job_id,
                    review_item_id=request.review_item_id,
                    claim_id=request.claim_id,
                    decision=request.decision,
                    reason=request.reason,
                    reviewer=request.reviewer,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise _conflict(exc) from exc

    @app.get("/v1/research/jobs/{job_id}/bundle")
    def get_research_job_bundle(
        job_id: str,
        service: ResearchJobService = Depends(get_service),
    ) -> JSONResponse:
        job = require_job(service, job_id)
        bundle_path = artifact_path_for_job(job, "report_bundle.json")
        if not bundle_path.exists():
            raise HTTPException(status_code=404, detail=f"missing artifact: {bundle_path.name}")
        return JSONResponse(load_json_artifact(bundle_path))

    @app.get("/v1/research/jobs/{job_id}/artifacts/{artifact_name:path}")
    def get_research_job_artifact(
        job_id: str,
        artifact_name: str,
        service: ResearchJobService = Depends(get_service),
    ) -> Response:
        if artifact_name not in ARTIFACT_NAME_CHOICES:
            raise HTTPException(status_code=404, detail=f"unsupported artifact: {artifact_name}")
        job = require_job(service, job_id)
        path = artifact_path_for_job(job, artifact_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"missing artifact: {artifact_name}")
        if path.suffix == ".json":
            return JSONResponse(load_json_artifact(path))
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            return HTMLResponse(content=content)
        if path.name.endswith(".jsonl"):
            return PlainTextResponse(content=content, media_type="application/x-ndjson")
        return PlainTextResponse(content=content)

    @app.post("/v1/batch/research", response_model=BatchResearchResponse, status_code=202)
    def submit_batch_research(
        request: BatchResearchRequest,
        service: ResearchJobService = Depends(get_service),
    ) -> BatchResearchResponse:
        return submit_batch_jobs(service, request.jobs)

    return app


app = create_app()


__all__ = ["app", "create_app"]
