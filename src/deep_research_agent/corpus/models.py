"""Pydantic contracts for the versioned research corpus."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


StoragePolicy = Literal[
    "mirror_allowed",
    "internal_processing",
    "derived_only",
    "link_only",
    "user_supplied",
]
PublicationStatus = Literal[
    "preprint",
    "submitted",
    "accepted",
    "published",
    "withdrawn",
    "retracted",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenDict(dict[str, Any]):
    """Dict-compatible mapping that rejects mutation after validation."""

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("mapping is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable

    def __ior__(self, other: Any):
        self._immutable(other)
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenDict:
        return type(self)(deepcopy(dict(self), memo))


class CorpusModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceDescriptor(CorpusModel):
    """Connector policy and provenance declaration for a source."""

    source_id: str = Field(min_length=1)
    source_role: str = Field(min_length=1)
    trust_tier: int = Field(default=3, ge=1, le=5)
    coverage: str = ""
    official_base_uri: str = ""
    access_method: str = ""
    authentication_mode: str = "none"
    rate_limit_policy: str = ""
    incremental_cursor_type: str = ""
    canonical_identifiers: list[str] = Field(default_factory=list)
    metadata_license: str | None = None
    license: str | None = None
    fulltext_license: str | None = None
    fulltext_license_strategy: str = "item-level"
    storage_policy: StoragePolicy = "link_only"
    redistribution_policy: str = "link-only"
    freshness_sla: str = ""
    fallback_sources: list[str] = Field(default_factory=list)
    health_probe: str = ""
    parser_name: str = "docling"
    parser_version: str = "1"
    supports_critical_claims: bool = True


class WorkRecord(CorpusModel):
    """Stable scholarly identity shared by multiple source versions."""

    work_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    external_ids: dict[str, str] = Field(default_factory=dict)
    publication_status: PublicationStatus = "preprint"
    venue: str | None = None
    publication_dates: dict[str, str] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    license: str | None = None
    locations: list[str] = Field(default_factory=list)
    citation_edges: list[str] = Field(default_factory=list)
    artifact_links: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentVersion(CorpusModel):
    """Immutable fetched/parsed representation of one work version."""

    document_version_id: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_native_id: str = Field(min_length=1)
    version_label: str = "v1"
    canonical_uri: str = ""
    published_at: datetime | None = None
    source_updated_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = "text/plain"
    license: str | None = None
    storage_policy: StoragePolicy = "link_only"
    source_role: str = "discovery"
    supports_critical_claims: bool = False
    parser_name: str = "docling"
    parser_version: str = "1"
    supersedes: str | None = None
    tenant_id: str | None = None
    title: str = ""
    text: str = ""
    abstract: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content_sha256", mode="before")
    @classmethod
    def _normalize_hash(cls, value: str) -> str:
        return str(value).lower()


class CorpusSnapshot(CorpusModel):
    """A point-in-time list of document versions used by one report."""

    snapshot_id: str = Field(min_length=1)
    tenant_id: str | None = None
    document_version_ids: tuple[str, ...] = ()
    content_hashes: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    frozen: bool = False

    @property
    def manifest_id(self) -> str:
        return self.snapshot_id


class CorpusManifest(CorpusModel):
    """Immutable corpus manifest returned before a report run starts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_id: str = Field(min_length=1)
    document_version_ids: tuple[str, ...] = ()
    content_hashes: dict[str, str] = Field(default_factory=dict)
    tenant_id: str | None = None
    frozen: bool = True

    @model_validator(mode="after")
    def _freeze_content_hashes(self) -> CorpusManifest:
        object.__setattr__(self, "content_hashes", FrozenDict(self.content_hashes))
        return self


class ParsedDocument(CorpusModel):
    """Parser-neutral document fields."""

    text: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
