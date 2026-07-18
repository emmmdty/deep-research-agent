"""Tenant-scoped topic workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    NonBlankText,
    ProductServiceDependency,
    StrictRequest,
)


router = APIRouter(prefix="/v1/topics", tags=["topics"])


class CreateTopicRequest(StrictRequest):
    title: NonBlankText = Field(max_length=500)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: CreateTopicRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    return service.create_topic(tenant_id=identity.tenant_id, user_id=identity.user_id, title=payload.title)


@router.get("")
def list_topics(identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    return {"topics": service.list_topics(tenant_id=identity.tenant_id)}


@router.get("/{topic_id}")
def get_topic(topic_id: str, identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    topic = service.get_topic(topic_id, tenant_id=identity.tenant_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return topic


__all__ = ["router"]
