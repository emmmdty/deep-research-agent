"""Snapshot store。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from deep_research_agent.connectors.utils import canonicalize_uri
from deep_research_agent.reporting.schemas import validate_instance


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapshotInput(BaseModel):
    """单次 snapshot 持久化输入。"""

    connector_name: str = Field(description="connector 名称")
    source_type: str = Field(description="来源类型")
    canonical_uri: str = Field(description="待归一化 URI")
    title: str = Field(description="标题")
    text: str = Field(description="抓取正文")
    mime_type: str = Field(default="text/plain", description="MIME 类型")
    auth_scope: str = Field(default="public", description="鉴权范围")
    query: str = Field(default="", description="触发查询")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    url: str = Field(default="", description="原始 URL")


class SnapshotManifest(BaseModel):
    """snapshot manifest。"""

    snapshot_id: str = Field(description="snapshot ID")
    canonical_uri: str = Field(description="归一化 URI")
    fetched_at: str = Field(description="抓取时间")
    content_hash: str = Field(description="内容 hash")
    mime_type: str = Field(description="MIME 类型")
    auth_scope: str = Field(description="鉴权范围")
    freshness_metadata: dict[str, Any] = Field(default_factory=dict, description="新鲜度元数据")


class SnapshotStore:
    """把抓取结果固化成 phase03 snapshot。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def persist(self, payload: SnapshotInput) -> SnapshotManifest:
        """持久化文本与 manifest。"""
        canonical_uri = canonicalize_uri(payload.canonical_uri or payload.url)
        snapshot_id = f"snapshot-{uuid4().hex[:12]}"
        fetched_at = _utc_now_iso()
        content_hash = sha256(payload.text.encode("utf-8")).hexdigest()
        freshness_metadata = {
            "query": payload.query,
            "published_at": payload.metadata.get("published_at"),
            "source_type": payload.source_type,
            "connector_name": payload.connector_name,
            **payload.metadata,
        }
        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            canonical_uri=canonical_uri,
            fetched_at=fetched_at,
            content_hash=content_hash,
            mime_type=payload.mime_type,
            auth_scope=payload.auth_scope,
            freshness_metadata=freshness_metadata,
        )
        manifest_payload = manifest.model_dump(mode="json")
        validate_instance("source-snapshot", manifest_payload)
        (self.root / f"{snapshot_id}.txt").write_text(payload.text, encoding="utf-8")
        (self.root / f"{snapshot_id}.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest
