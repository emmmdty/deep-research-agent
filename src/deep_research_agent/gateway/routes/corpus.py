"""Private tenant corpus upload and read routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    ProductServiceDependency,
)


router = APIRouter(prefix="/v1/corpus", tags=["corpus"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_corpus(
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
    file: UploadFile = File(...),
) -> dict:
    try:
        content = await file.read()
        return service.upload_corpus(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            filename=file.filename or "upload.bin",
            media_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("")
def list_corpus(identity: IdentityDependency, service: ProductServiceDependency) -> dict:
    return {"documents": service.list_corpus(tenant_id=identity.tenant_id)}


@router.get("/{document_id}")
def get_corpus(
    document_id: str,
    identity: IdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    document = service.get_corpus(document_id, tenant_id=identity.tenant_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return document


__all__ = ["router"]
