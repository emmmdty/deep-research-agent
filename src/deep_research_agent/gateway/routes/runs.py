"""Run lifecycle, bundle, and reconnectable event stream routes."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Body, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    NonBlankText,
    ProductServiceDependency,
    StrictRequest,
)


router = APIRouter(tags=["runs"])


class CreateRunRequest(StrictRequest):
    question: NonBlankText
    topic_id: str | None = None
    conversation_id: str | None = None
    start_worker: bool | None = None


class ResumeRunRequest(StrictRequest):
    start_worker: bool | None = None


def _require_run(service, run_id: str, tenant_id: str) -> dict:
    run = service.get_run(run_id, tenant_id=tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post("/v1/topics/{topic_id}/runs", status_code=status.HTTP_202_ACCEPTED)
def create_topic_run(
    topic_id: str,
    payload: CreateRunRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        return service.create_run(
            topic_id=topic_id,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            start_worker=payload.start_worker,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="topic or conversation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/v1/runs", status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: CreateRunRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    topic_id = payload.topic_id
    if topic_id is None and payload.conversation_id is not None:
        conversation = service.repository.get_conversation(
            payload.conversation_id, tenant_id=identity.tenant_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="conversation not found")
        topic_id = conversation.topic_id
    if topic_id is None:
        raise HTTPException(status_code=422, detail="topic_id or conversation_id is required")
    try:
        return service.create_run(
            topic_id=topic_id,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            start_worker=payload.start_worker,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="topic or conversation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/v1/topics/{topic_id}/runs")
def list_topic_runs(
    topic_id: str,
    identity: IdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        return {"runs": service.list_runs(tenant_id=identity.tenant_id, topic_id=topic_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="topic not found") from exc


@router.get("/v1/runs/{run_id}")
def get_run(run_id: str, identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    return _require_run(service, run_id, identity.tenant_id)


@router.post("/v1/runs/{run_id}:cancel")
def cancel_run(
    run_id: str,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        run = service.cancel_run(run_id, tenant_id=identity.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post("/v1/runs/{run_id}:resume")
def resume_run(
    run_id: str,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
    payload: ResumeRunRequest | None = Body(default=None),
) -> dict:
    try:
        run = service.resume_run(
            run_id,
            tenant_id=identity.tenant_id,
            start_worker=payload.start_worker if payload is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/v1/runs/{run_id}/bundle")
def get_bundle(run_id: str, identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    try:
        bundle = service.get_bundle(run_id, tenant_id=identity.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    if bundle is None:
        raise HTTPException(status_code=404, detail="run bundle is not available")
    return bundle


def _sse_frame(event: dict) -> str:
    payload = json.dumps(event["payload"], separators=(",", ":"), sort_keys=True)
    return (
        f"id: {event['event_id']}\n"
        f"event: {event['event_type']}\n"
        f"data: {payload}\n\n"
    )


@router.get("/v1/runs/{run_id}/events")
async def run_events(
    run_id: str,
    request: Request,
    identity: IdentityDependency,
    service: ProductServiceDependency,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    after_sequence = 0
    if last_event_id:
        try:
            after_sequence = int(last_event_id.rsplit(":", 1)[-1])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Last-Event-ID must be numeric") from exc
    if service.get_run(run_id, tenant_id=identity.tenant_id) is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def stream() -> AsyncIterator[str]:
        cursor = after_sequence
        started_at = time.monotonic()
        heartbeat_at = started_at + request.app.state.event_heartbeat_interval_seconds
        try:
            while time.monotonic() - started_at < request.app.state.event_stream_timeout_seconds:
                if await request.is_disconnected():
                    return
                events = service.list_run_events(
                    run_id,
                    tenant_id=identity.tenant_id,
                    after_sequence=cursor,
                )
                if events is None:
                    return
                if events:
                    for event in events:
                        cursor = max(cursor, int(event["sequence"]))
                        yield _sse_frame(event)
                        if event["payload"].get("terminal"):
                            return
                now = time.monotonic()
                if now >= heartbeat_at:
                    yield ": heartbeat\n\n"
                    heartbeat_at = now + request.app.state.event_heartbeat_interval_seconds
                await asyncio.sleep(request.app.state.event_poll_interval_seconds)
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
