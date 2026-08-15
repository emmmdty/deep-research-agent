"""Private tenant corpus upload and read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from deep_research_agent.gateway.routes.auth import (
    CsrfIdentityDependency,
    IdentityDependency,
    ProductServiceDependency,
    tenant_rate_limited,
)

router = APIRouter(prefix="/v1/corpus", tags=["corpus"])

# 上传体上限：星形/FastAPI 默认不限制 multipart 体积，一个无限大的文件会
# 直接把整个请求读进内存并整块落库（无界内存 + 无界 DB 增长）。
_MAX_CORPUS_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_corpus(
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
    file: UploadFile = File(...),
    _limited: None = Depends(tenant_rate_limited("v1.corpus.upload")),
) -> dict:
    try:
        content = await _read_limited(file, _MAX_CORPUS_UPLOAD_BYTES)
        return service.upload_corpus(
            tenant_id=identity.tenant_id,
            user_id=identity.user_id,
            filename=file.filename or "upload.bin",
            media_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """流式读取上传体并强制上限：超限立即 413，不等整包读完。"""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"corpus upload exceeds the {max_bytes}-byte limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


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
