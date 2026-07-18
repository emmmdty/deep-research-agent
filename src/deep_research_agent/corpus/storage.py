"""Repository protocols and in-memory adapters for Task 5 persistence."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from .models import CorpusSnapshot, DocumentVersion, SourceDescriptor, WorkRecord


class CorpusRepository(Protocol):
    def save_source(self, source: SourceDescriptor) -> None: ...

    def get_source(self, source_id: str) -> SourceDescriptor | None: ...

    def save_work(self, work: WorkRecord) -> None: ...

    def get_work(self, work_id: str) -> WorkRecord | None: ...

    def find_work(
        self, *, source_id: str, source_native_id: str, tenant_id: str | None = None
    ) -> WorkRecord | None: ...

    def save_document(self, document: DocumentVersion) -> None: ...

    def get_document(self, document_version_id: str) -> DocumentVersion | None: ...

    def list_documents(self, *, tenant_id: str | None = None) -> list[DocumentVersion]: ...

    def find_cached(self, cache_key: str) -> DocumentVersion | None: ...

    def save_cache(self, cache_key: str, document: DocumentVersion) -> None: ...

    def grant(
        self,
        document_version_id: str,
        tenant_id: str,
        *,
        actor_tenant_id: str | None = None,
        actor_is_admin: bool = False,
    ) -> None: ...

    def can_read(self, document: DocumentVersion, tenant_id: str | None) -> bool: ...

    def save_snapshot(self, snapshot: CorpusSnapshot) -> None: ...

    def get_snapshot(self, snapshot_id: str) -> CorpusSnapshot | None: ...


class SQLCorpusRepository(Protocol):
    """Production persistence boundary reserved for Task 5."""

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> object: ...


class InMemoryCorpusRepository:
    def __init__(self) -> None:
        self.sources: dict[str, SourceDescriptor] = {}
        self.works: dict[str, WorkRecord] = {}
        self.documents: dict[str, DocumentVersion] = {}
        self.cache: dict[str, str] = {}
        self.grants: dict[str, set[str]] = {}
        self.snapshots: dict[str, CorpusSnapshot] = {}

    def save_source(self, source: SourceDescriptor) -> None:
        existing = self.sources.get(source.source_id)
        if existing is not None and existing != source:
            raise ValueError(f"source {source.source_id!r} already exists with different policy")
        self.sources[source.source_id] = deepcopy(source)

    def get_source(self, source_id: str) -> SourceDescriptor | None:
        source = self.sources.get(source_id)
        return deepcopy(source) if source is not None else None

    def save_work(self, work: WorkRecord) -> None:
        existing = self.works.get(work.work_id)
        if existing is not None and existing != work:
            raise ValueError(f"work {work.work_id!r} already exists with different identity")
        self.works[work.work_id] = deepcopy(work)

    def get_work(self, work_id: str) -> WorkRecord | None:
        work = self.works.get(work_id)
        return deepcopy(work) if work is not None else None

    def find_work(
        self, *, source_id: str, source_native_id: str, tenant_id: str | None = None
    ) -> WorkRecord | None:
        for work in self.works.values():
            if work.external_ids.get(source_id) == source_native_id and work.tenant_id == tenant_id:
                return deepcopy(work)
        return None

    def save_document(self, document: DocumentVersion) -> None:
        existing = self.documents.get(document.document_version_id)
        if existing is not None and existing != document:
            if existing.model_dump(exclude={"retrieved_at"}) != document.model_dump(exclude={"retrieved_at"}):
                raise ValueError(f"document version {document.document_version_id!r} is immutable")
            return
        self.documents[document.document_version_id] = deepcopy(document)

    def get_document(self, document_version_id: str) -> DocumentVersion | None:
        document = self.documents.get(document_version_id)
        return deepcopy(document) if document is not None else None

    def list_documents(self, *, tenant_id: str | None = None) -> list[DocumentVersion]:
        documents = list(self.documents.values()) if tenant_id is None else [
            doc for doc in self.documents.values() if doc.tenant_id == tenant_id
        ]
        return deepcopy(documents)

    def find_cached(self, cache_key: str) -> DocumentVersion | None:
        document_id = self.cache.get(cache_key)
        document = self.documents.get(document_id) if document_id else None
        return deepcopy(document) if document is not None else None

    def save_cache(self, cache_key: str, document: DocumentVersion) -> None:
        self.cache.setdefault(cache_key, document.document_version_id)

    def grant(
        self,
        document_version_id: str,
        tenant_id: str,
        *,
        actor_tenant_id: str | None = None,
        actor_is_admin: bool = False,
    ) -> None:
        document = self.documents.get(document_version_id)
        if document is None:
            raise KeyError(f"unknown document version {document_version_id!r}")
        if document.tenant_id is None:
            raise ValueError("public documents do not need tenant grants")
        if actor_tenant_id != document.tenant_id:
            raise PermissionError("only the owning tenant or an admin may grant document access")
        self.grants.setdefault(document_version_id, set()).add(tenant_id)

    def can_read(self, document: DocumentVersion, tenant_id: str | None) -> bool:
        if document.tenant_id is None:
            return tenant_id is not None or tenant_id is None
        if tenant_id == document.tenant_id:
            return True
        return tenant_id is not None and tenant_id in self.grants.get(document.document_version_id, set())

    def save_snapshot(self, snapshot: CorpusSnapshot) -> None:
        existing = self.snapshots.get(snapshot.snapshot_id)
        if existing is not None and existing != snapshot:
            raise ValueError(f"snapshot {snapshot.snapshot_id!r} is immutable")
        self.snapshots[snapshot.snapshot_id] = deepcopy(snapshot)

    def get_snapshot(self, snapshot_id: str) -> CorpusSnapshot | None:
        snapshot = self.snapshots.get(snapshot_id)
        return deepcopy(snapshot) if snapshot is not None else None
