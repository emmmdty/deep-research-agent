"""Tenant/user scoped memory CRUD and export routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    ProductServiceDependency,
    StrictRequest,
)


router = APIRouter(prefix="/v1/memory", tags=["memory"])


class CreateMemoryRequest(StrictRequest):
    scope: str = Field(min_length=1)
    content: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


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
            content=payload.content,
            confidence=payload.confidence,
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
