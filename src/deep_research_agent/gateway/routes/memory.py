"""Tenant/user scoped memory CRUD and export routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import Field
from typing import Literal

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    ProductServiceDependency,
    StrictRequest,
)


router = APIRouter(prefix="/v1/memory", tags=["memory"])


class CreateMemoryRequest(StrictRequest):
    scope: str = Field(min_length=1)
    subject_id: str | None = Field(default=None, min_length=1, max_length=128)
    content: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    key: str | None = Field(default=None, min_length=1)
    provenance: dict = Field(default_factory=dict)
    sensitivity: Literal["normal", "sensitive"] = "normal"
    ttl_seconds: int | None = Field(default=None, gt=0)
    confirm_sensitive: bool = False


class UpdateMemoryRequest(StrictRequest):
    content: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


@router.get("/export")
def export_memory(identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    return {"memories": service.list_memories(tenant_id=identity.tenant_id, user_id=identity.user_id)}


@router.get("")
def list_memory(identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    return {"memories": service.list_memories(tenant_id=identity.tenant_id, user_id=identity.user_id)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: CreateMemoryRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        return service.create_memory(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            scope=payload.scope,
            subject_id=payload.subject_id,
            content=payload.content,
            confidence=payload.confidence,
            key=payload.key,
            provenance=payload.provenance,
            sensitivity=payload.sensitivity,
            ttl_seconds=payload.ttl_seconds,
            confirm_sensitive=payload.confirm_sensitive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{memory_id}")
def get_memory(memory_id: str, identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    memory = service.get_memory(memory_id, tenant_id=identity.tenant_id, user_id=identity.user_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return memory


@router.patch("/{memory_id}")
def update_memory(
    memory_id: str,
    payload: UpdateMemoryRequest,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        memory = service.update_memory(
            memory_id,
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            content=payload.content,
            confidence=payload.confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if memory is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> None:
    if not service.repository.delete_memory(
        memory_id, tenant_id=identity.tenant_id, user_id=identity.user_id
    ):
        raise HTTPException(status_code=404, detail="memory not found")


__all__ = ["router"]
