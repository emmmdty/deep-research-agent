"""FastAPI surface for the deterministic research job runtime."""

from __future__ import annotations

import hmac
import os
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from deep_research_agent.gateway.artifacts import (
    ARTIFACT_NAME_CHOICES,
    artifact_path_for_job,
    load_json_artifact,
)
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
from deep_research_agent.gateway.routes import PRODUCT_ROUTERS
from deep_research_agent.gateway.routes.auth import rate_limited
from deep_research_agent.observability.tracing import configure_tracing
from deep_research_agent.product.db import create_database
from deep_research_agent.product.ratelimit import RateLimiter, TokenBucketRateLimiter
from deep_research_agent.product.service import ProductService
from deep_research_agent.research_jobs import ResearchJobService

ServiceFactory = Callable[[], ResearchJobService]


def render_research_metrics() -> tuple[str, str] | None:
    """Render the Prometheus exposition; None when the optional client is absent."""

    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    except ImportError:
        return None
    from deep_research_agent.observability.cost_tracker import (
        prometheus_registry,
        refresh_prometheus_gauges,
    )

    registry = prometheus_registry()
    if registry is None:
        return None
    refresh_prometheus_gauges()
    return generate_latest(registry).decode("utf-8"), CONTENT_TYPE_LATEST


def create_app(
    *,
    service_factory: ServiceFactory | None = None,
    database_url: str | None = None,
    offline_mode: bool = False,
    product_database_url: str | None = None,
    product_offline_mode: bool | None = None,
    allow_public_registration: bool | None = None,
    bootstrap_admin_email: str | None = None,
    bootstrap_admin_password: str | None = None,
    event_poll_interval_seconds: float | None = None,
    event_heartbeat_interval_seconds: float | None = None,
    event_stream_timeout_seconds: float | None = None,
    api_key: str | None = None,
    ratelimiter: RateLimiter | None = None,
) -> FastAPI:
    """Create the local Phase 4 HTTP API."""

    configure_tracing()
    factory = service_factory or ResearchJobService
    runtime_service = factory()
    app = FastAPI(
        title="Deep Research Agent API",
        version="0.1.0",
        summary="Deterministic HTTP surface for async research jobs and report bundles.",
    )

    resolved_database_url = (
        product_database_url
        or database_url
        or os.environ.get("PRODUCT_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    configured_offline_mode = os.environ.get("PRODUCT_OFFLINE_MODE")
    if product_offline_mode is None and configured_offline_mode is not None:
        resolved_offline_mode = configured_offline_mode.strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
    else:
        resolved_offline_mode = (
            offline_mode if product_offline_mode is None else product_offline_mode
        )
    resolved_public_registration = (
        resolved_offline_mode
        if allow_public_registration is None
        else bool(allow_public_registration)
    )
    resolved_bootstrap_email = bootstrap_admin_email or os.environ.get(
        "DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_EMAIL"
    )
    resolved_bootstrap_password = bootstrap_admin_password or os.environ.get(
        "DEEP_RESEARCH_AGENT_BOOTSTRAP_ADMIN_PASSWORD"
    )
    if bool(resolved_bootstrap_email) != bool(resolved_bootstrap_password):
        raise ValueError("bootstrap admin email and password must both be configured")
    resolved_event_poll = (
        (0.05 if resolved_offline_mode else 0.25)
        if event_poll_interval_seconds is None
        else event_poll_interval_seconds
    )
    resolved_event_heartbeat = (
        (0.1 if resolved_offline_mode else 15.0)
        if event_heartbeat_interval_seconds is None
        else event_heartbeat_interval_seconds
    )
    resolved_event_timeout = (
        (0.5 if resolved_offline_mode else 300.0)
        if event_stream_timeout_seconds is None
        else event_stream_timeout_seconds
    )
    if min(resolved_event_poll, resolved_event_heartbeat, resolved_event_timeout) <= 0:
        raise ValueError("event stream timing values must be positive")
    product_service: ProductService | None = None
    if resolved_database_url is None and resolved_offline_mode:
        resolved_database_url = "sqlite+pysqlite:///:memory:"
    if resolved_database_url is not None:
        product_database = create_database(
            resolved_database_url, offline_mode=resolved_offline_mode
        )
        product_database.create_schema()
        product_service = ProductService(
            product_database,
            runtime_service=runtime_service,
        )
        if resolved_bootstrap_email and resolved_bootstrap_password:
            product_service.bootstrap_admin(
                email=resolved_bootstrap_email,
                password=resolved_bootstrap_password,
            )
    elif resolved_bootstrap_email or resolved_bootstrap_password:
        raise ValueError("bootstrap admin requires a configured product database")
    app.state.product_service = product_service
    app.state.allow_public_registration = resolved_public_registration
    app.state.runtime_service = runtime_service
    app.state.event_poll_interval_seconds = resolved_event_poll
    app.state.event_heartbeat_interval_seconds = resolved_event_heartbeat
    app.state.event_stream_timeout_seconds = resolved_event_timeout
    app.state.legacy_master_key = api_key or os.environ.get("DEEP_RESEARCH_AGENT_MASTER_KEY")
    app.state.ratelimiter = ratelimiter if ratelimiter is not None else TokenBucketRateLimiter()

    def get_service() -> ResearchJobService:
        return runtime_service

    def require_job(service: ResearchJobService, job_id: str):
        job = service.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
        return job

    def require_legacy_job(service: ResearchJobService, job_id: str):
        """Keep tenant-scoped product jobs out of the unauthenticated legacy API."""
        job = require_job(service, job_id)
        if job.metadata.get("product_tenant_id") is not None:
            raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
        return job

    def require_legacy_api_key(
        request: Request,
        api_key_header: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        """Legacy jobs API 鉴权：X-API-Key 必须匹配 master key，fail closed。"""
        configured = getattr(request.app.state, "legacy_master_key", None)
        if not configured:
            raise HTTPException(
                status_code=503,
                detail="the legacy API requires DEEP_RESEARCH_AGENT_MASTER_KEY",
            )
        if not api_key_header or not hmac.compare_digest(api_key_header, configured):
            raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")

    def _conflict(error: Exception) -> HTTPException:
        return HTTPException(status_code=409, detail=str(error))

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "deep-research-agent",
            "version": "0.1.0",
        }

    @app.get("/metrics")
    def metrics() -> Response:
        rendered = render_research_metrics()
        if rendered is None:
            raise HTTPException(
                status_code=503,
                detail="prometheus-client is not installed; install prometheus-client to enable /metrics",
            )
        body, content_type = rendered
        return Response(content=body, media_type=content_type)

    @app.post("/v1/research/jobs", response_model=PublicJobResponse, status_code=202)
    def submit_research_job(
        request: SubmitJobRequest,
        service: ResearchJobService = Depends(get_service),
        _auth: None = Depends(require_legacy_api_key),
        _limited: None = Depends(rate_limited("anonymous:v1.research.jobs")),
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
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        return public_job_response(require_legacy_job(service, job_id))

    @app.get("/v1/research/jobs/{job_id}/events", response_model=JobEventsResponse)
    def get_research_job_events(
        job_id: str,
        after_sequence: int = Query(default=0, ge=0),
        service: ResearchJobService = Depends(get_service),
        _auth: None = Depends(require_legacy_api_key),
    ) -> JobEventsResponse:
        require_legacy_job(service, job_id)
        events = [
            public_job_event(item)
            for item in service.list_events(job_id, after_sequence=after_sequence)
        ]
        return JobEventsResponse(job_id=job_id, events=events)

    @app.post("/v1/research/jobs/{job_id}:cancel", response_model=PublicJobResponse)
    def cancel_research_job(
        job_id: str,
        _: EmptyRequest,
        service: ResearchJobService = Depends(get_service),
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        try:
            require_legacy_job(service, job_id)
            return public_job_response(service.cancel(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/research/jobs/{job_id}:retry", response_model=PublicJobResponse)
    def retry_research_job(
        job_id: str,
        request: RetryJobRequest,
        service: ResearchJobService = Depends(get_service),
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        try:
            require_legacy_job(service, job_id)
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
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        try:
            require_legacy_job(service, job_id)
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
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        try:
            require_legacy_job(service, job_id)
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
        _auth: None = Depends(require_legacy_api_key),
    ) -> PublicJobResponse:
        try:
            require_legacy_job(service, job_id)
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
        _auth: None = Depends(require_legacy_api_key),
    ) -> JSONResponse:
        job = require_legacy_job(service, job_id)
        bundle_path = artifact_path_for_job(job, "report_bundle.json")
        if not bundle_path.exists():
            raise HTTPException(status_code=404, detail=f"missing artifact: {bundle_path.name}")
        return JSONResponse(load_json_artifact(bundle_path))

    @app.get("/v1/research/jobs/{job_id}/artifacts/{artifact_name:path}")
    def get_research_job_artifact(
        job_id: str,
        artifact_name: str,
        service: ResearchJobService = Depends(get_service),
        _auth: None = Depends(require_legacy_api_key),
    ) -> Response:
        if artifact_name not in ARTIFACT_NAME_CHOICES:
            raise HTTPException(status_code=404, detail=f"unsupported artifact: {artifact_name}")
        job = require_legacy_job(service, job_id)
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
        _auth: None = Depends(require_legacy_api_key),
        _limited: None = Depends(rate_limited("anonymous:v1.batch.research")),
    ) -> BatchResearchResponse:
        return submit_batch_jobs(service, request.jobs)

    for router in PRODUCT_ROUTERS:
        app.include_router(router)

    return app


app = create_app()


__all__ = ["app", "create_app"]
