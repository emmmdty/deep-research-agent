"""Repository protocols and in-memory adapters for Task 5 persistence."""

from __future__ import annotations

from typing import Protocol

from .models import CorpusSnapshot, DocumentVersion, SourceDescriptor, WorkRecord


class CorpusRepository(Protocol):
    def save_source(self, source: SourceDescriptor) -> None: ...

    def get_source(self, source_id: str) -> SourceDescriptor | None: ...

    def save_work(self, work: WorkRecord) -> None: ...

    def get_work(self, work_id: str) -> WorkRecord | None: ...

    def find_work(self, *, source_id: str, source_native_id: str) -> WorkRecord | None: ...

    def save_document(self, document: DocumentVersion) -> None: ...

    def get_document(self, document_version_id: str) -> DocumentVersion | None: ...

    def list_documents(self, *, tenant_id: str | None = None) -> list[DocumentVersion]: ...

    def find_cached(self, cache_key: str) -> DocumentVersion | None: ...

    def save_cache(self, cache_key: str, document: DocumentVersion) -> None: ...

    def grant(self, document_version_id: str, tenant_id: str) -> None: ...

    def can_read(self, document: DocumentVersion, tenant_id: str | None) -> bool: ...

    def save_snapshot(self, snapshot: CorpusSnapshot) -> None: ...


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
        self.sources[source.source_id] = source

    def get_source(self, source_id: str) -> SourceDescriptor | None:
        return self.sources.get(source_id)

    def save_work(self, work: WorkRecord) -> None:
        existing = self.works.get(work.work_id)
        if existing is not None and existing != work:
            raise ValueError(f"work {work.work_id!r} already exists with different identity")
        self.works[work.work_id] = work

    def get_work(self, work_id: str) -> WorkRecord | None:
        return self.works.get(work_id)

    def find_work(self, *, source_id: str, source_native_id: str) -> WorkRecord | None:
        for work in self.works.values():
            if work.external_ids.get(source_id) == source_native_id:
                return work
        return None

    def save_document(self, document: DocumentVersion) -> None:
        existing = self.documents.get(document.document_version_id)
        if existing is not None and existing != document:
            raise ValueError(f"document version {document.document_version_id!r} is immutable")
        self.documents[document.document_version_id] = document

    def get_document(self, document_version_id: str) -> DocumentVersion | None:
        return self.documents.get(document_version_id)

    def list_documents(self, *, tenant_id: str | None = None) -> list[DocumentVersion]:
        return list(self.documents.values()) if tenant_id is None else [
            doc for doc in self.documents.values() if doc.tenant_id == tenant_id
        ]

    def find_cached(self, cache_key: str) -> DocumentVersion | None:
        document_id = self.cache.get(cache_key)
        return self.documents.get(document_id) if document_id else None

    def save_cache(self, cache_key: str, document: DocumentVersion) -> None:
        self.cache.setdefault(cache_key, document.document_version_id)

    def grant(self, document_version_id: str, tenant_id: str) -> None:
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
        self.snapshots[snapshot.snapshot_id] = snapshot
