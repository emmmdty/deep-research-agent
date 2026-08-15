"""Conversation message routing and structured research decisions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    NonBlankText,
    ProductServiceDependency,
    StrictRequest,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


class MessageRequest(StrictRequest):
    content: NonBlankText
    refresh: bool = False


@router.post("/{conversation_id}/messages")
def post_message(
    conversation_id: str,
    payload: MessageRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> JSONResponse:
    try:
        result = service.respond_to_message(
            conversation_id,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            content=payload.content,
            refresh=payload.refresh,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="conversation not found") from exc
    status_code = 202 if result["response_type"] == "research_job_started" else 200
    return JSONResponse(result, status_code=status_code)


__all__ = ["router"]
