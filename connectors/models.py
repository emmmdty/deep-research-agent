"""Phase 03 connector substrate 数据模型。"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class ConnectorCandidate(BaseModel):
    """统一 search candidate。"""

    connector_name: str = Field(description="connector 名称")
    source_type: str = Field(description="来源类型")
    title: str = Field(description="候选标题")
    canonical_uri: str = Field(description="归一化 URI")
    query: str = Field(description="触发查询")
    snippet: str = Field(default="", description="候选摘要")
    published_at: str | None = Field(default=None, description="发布时间")
    auth_scope: str = Field(default="public", description="鉴权范围")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    @property
    def domain(self) -> str:
        parsed = urlparse(self.canonical_uri)
        return parsed.netloc.lower()


class ConnectorFetchResult(BaseModel):
    """统一 fetch/file-ingest 结果。"""

    connector_name: str = Field(description="connector 名称")
    source_type: str = Field(description="来源类型")
    title: str = Field(description="文档标题")
    canonical_uri: str = Field(description="归一化 URI")
    query: str = Field(description="触发查询")
    text: str = Field(description="抓取后的正文")
    snippet: str = Field(default="", description="摘要")
    mime_type: str = Field(default="text/plain", description="文档 MIME 类型")
    auth_scope: str = Field(default="public", description="鉴权范围")
    freshness_metadata: dict[str, Any] = Field(default_factory=dict, description="新鲜度元数据")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    url: str = Field(default="", description="原始 URL")


class ConnectorHealthRecord(BaseModel):
    """connector 健康统计。"""

    connector_name: str = Field(description="connector 名称")
    search_attempts: int = Field(default=0, description="search 尝试次数")
    search_successes: int = Field(default=0, description="search 成功次数")
    fetch_attempts: int = Field(default=0, description="fetch 尝试次数")
    fetch_successes: int = Field(default=0, description="fetch 成功次数")
    policy_blocked: int = Field(default=0, description="被 policy 拦截次数")
    error_count: int = Field(default=0, description="错误次数")
    last_error: str | None = Field(default=None, description="最近错误")
