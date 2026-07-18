"""Corpus ingestion, retrieval, authorization, and manifest freezing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from datetime import datetime

from .models import (
    CorpusSnapshot,
    DocumentVersion,
    ParsedDocument,
    SourceDescriptor,
    WorkRecord,
    utc_now,
)
from .parsers import DoclingParser, GrobidParser, ScholarlyParser
from .storage import CorpusRepository, InMemoryCorpusRepository
from deep_research_agent.kernel.contracts import CorpusManifest


def _digest(value: bytes | str) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class CorpusService:
    """Own deterministic corpus state; connectors only supply typed inputs."""

    def __init__(
        self,
        *,
        repository: CorpusRepository | None = None,
        parsers: Iterable[ScholarlyParser] | None = None,
        clock=utc_now,
        grant_authorizer: Callable[[str | None, str, bool], bool] | None = None,
    ) -> None:
        self.repository = repository or InMemoryCorpusRepository()
        self.parsers = list(parsers or (GrobidParser(), DoclingParser()))
        if not self.parsers:
            raise ValueError("at least one scholarly parser is required")
        self.clock = clock
        self.grant_authorizer = grant_authorizer

    @staticmethod
    def cache_key(content_sha256: str, parser_name: str, parser_version: str) -> str:
        """Return the public shared-cache key, excluding all tenant identity."""

        return f"{content_sha256}:{parser_name}:{parser_version}"

    def ingest(
        self,
        *,
        source: SourceDescriptor,
        content: bytes | str,
        title: str = "",
        source_native_id: str,
        tenant_id: str | None = None,
        work_id: str | None = None,
        version_label: str = "v1",
        canonical_uri: str = "",
        media_type: str = "application/pdf",
        published_at: datetime | None = None,
        source_updated_at: datetime | None = None,
        license: str | None = None,
        supersedes: str | None = None,
        critical_claim: bool | None = None,
    ) -> DocumentVersion:
        """Validate policy, parse content, and persist an immutable version."""

        effective_license = license or source.license or source.fulltext_license
        if not source.supports_critical_claims and critical_claim is None:
            raise PermissionError("discovery-only sources require an explicit non-critical ingestion")
        if critical_claim and not source.supports_critical_claims:
            raise PermissionError("discovery-only sources cannot support critical claims")
        if tenant_id is not None and not tenant_id.strip():
            raise ValueError("tenant_id cannot be blank")
        self._validate_storage_policy(source, tenant_id=tenant_id, content=content, license=effective_license)
        self.repository.save_source(source)
        content_hash = _digest(content)
        private = tenant_id is not None or source.storage_policy in {"user_supplied", "internal_processing"}
        # A public cache entry is deliberately never used for private documents.
        cache_key = self.cache_key(content_hash, source.parser_name, source.parser_version)
        cached = None if private else self.repository.find_cached(cache_key)
        if cached is not None and (
            cached.source_id == source.source_id
            and cached.source_native_id == source_native_id
            and cached.version_label == version_label
            and cached.tenant_id is None
        ):
            return cached

        work = self.repository.find_work(
            source_id=source.source_id,
            source_native_id=source_native_id,
            tenant_id=tenant_id,
        )
        if work is None:
            work_identity = "\0".join((source.source_id, source_native_id, tenant_id or "public"))
            resolved_work_id = work_id or f"work:{_digest(work_identity)[:24]}"
            work = WorkRecord(
                work_id=resolved_work_id,
                title=title or source_native_id,
                external_ids={source.source_id: source_native_id},
                license=effective_license,
                tenant_id=tenant_id,
            )
            self.repository.save_work(work)
        elif work_id is not None and work.work_id != work_id:
            raise ValueError("work_id conflicts with the existing source identity")

        parsed, parser = self._parse_with_cached_fallback(content, media_type=media_type)
        document_id = self._document_id(
            work.work_id,
            source.source_id,
            source_native_id,
            version_label,
            content_hash,
            tenant_id,
            parser.name,
            parser.version,
        )
        derived_only = source.storage_policy == "derived_only"
        stored_metadata = {
            "authors": parsed.authors,
            "storage_policy": source.storage_policy,
            "content_sha256": content_hash,
            "content_length": len(content),
        }
        if derived_only:
            stored_metadata["section_names"] = list(parsed.sections)
            stored_metadata["derived_fields"] = {"title": parsed.title, "abstract": parsed.abstract}
        else:
            stored_metadata["sections"] = parsed.sections
            stored_metadata.update(parsed.metadata)
        document = DocumentVersion(
            document_version_id=document_id,
            work_id=work.work_id,
            source_id=source.source_id,
            source_native_id=source_native_id,
            version_label=version_label,
            canonical_uri=canonical_uri,
            published_at=published_at,
            source_updated_at=source_updated_at,
            retrieved_at=self.clock(),
            content_sha256=content_hash,
            media_type=media_type,
            license=effective_license,
            storage_policy=source.storage_policy,
            source_role=source.source_role,
            supports_critical_claims=source.supports_critical_claims,
            parser_name=parser.name,
            parser_version=parser.version,
            supersedes=supersedes,
            tenant_id=tenant_id,
            title=parsed.title or title or work.title,
            text="" if derived_only else parsed.text,
            abstract=parsed.abstract,
            metadata=stored_metadata,
        )
        self.repository.save_document(document)
        if private:
            if tenant_id is None:
                raise ValueError("private content requires a tenant_id")
            self.repository.grant(
                document.document_version_id,
                tenant_id,
                actor_tenant_id=tenant_id,
            )
        elif source.storage_policy == "mirror_allowed":
            self.repository.save_cache(self.cache_key(content_hash, parser.name, parser.version), document)
        return self.repository.get_document(document.document_version_id) or document

    def require_critical_claim_support(self, document_version_id: str, *, tenant_id: str | None) -> DocumentVersion:
        """Return a document only when its persisted source policy permits critical claims."""

        document = self.get_document(document_version_id, tenant_id=tenant_id)
        if not document.supports_critical_claims:
            raise PermissionError("document source cannot support critical claims")
        return document

    def grant_access(
        self,
        document_version_id: str,
        *,
        tenant_id: str,
        actor_tenant_id: str | None = None,
        actor_is_admin: bool = False,
        actor_role: str | None = None,
    ) -> None:
        """Grant a tenant access to one private document without changing its owner."""

        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be blank")
        if actor_tenant_id is not None and not actor_tenant_id.strip():
            raise ValueError("actor_tenant_id cannot be blank")
        document = self.repository.get_document(document_version_id)
        if document is None:
            raise KeyError(f"unknown document version {document_version_id!r}")
        if document.tenant_id is None:
            raise ValueError("public documents do not need tenant grants")
        is_admin = actor_is_admin or actor_role == "admin"
        if actor_tenant_id != document.tenant_id:
            if self.grant_authorizer is None or not self.grant_authorizer(
                actor_tenant_id, document.tenant_id, is_admin
            ):
                raise PermissionError("only the owning tenant or an authorized admin may grant access")
            actor_tenant_id = document.tenant_id
        self.repository.grant(
            document_version_id,
            tenant_id,
            actor_tenant_id=actor_tenant_id,
            actor_is_admin=False,
        )

    def get_document(self, document_version_id: str, *, tenant_id: str | None) -> DocumentVersion:
        document = self.repository.get_document(document_version_id)
        if document is None:
            raise KeyError(f"unknown document version {document_version_id!r}")
        if not self.repository.can_read(document, tenant_id):
            raise PermissionError("document is outside the authorized tenant")
        return document

    def search(self, query: str, *, tenant_id: str | None) -> list[DocumentVersion]:
        terms = [term for term in query.casefold().split() if term]
        results: list[DocumentVersion] = []
        for document in self.repository.list_documents(tenant_id=None):
            if not self.repository.can_read(document, tenant_id):
                continue
            haystack = " ".join((document.title, document.abstract, document.text)).casefold()
            if not terms or all(term in haystack for term in terms):
                results.append(document)
        return sorted(results, key=lambda item: item.document_version_id)

    def freeze_manifest(
        self,
        document_version_ids: Iterable[str] | None = None,
        *,
        tenant_id: str | None = None,
    ) -> CorpusManifest:
        if document_version_ids is None:
            candidates = [
                document
                for document in self.repository.list_documents(tenant_id=None)
                if self.repository.can_read(document, tenant_id)
            ]
        else:
            candidates = [self.get_document(document_id, tenant_id=tenant_id) for document_id in document_version_ids]
        candidates = sorted({document.document_version_id: document for document in candidates}.values(), key=lambda d: d.document_version_id)
        ids = tuple(document.document_version_id for document in candidates)
        hashes = {document.document_version_id: document.content_sha256 for document in candidates}
        critical_claims_allowed = {
            document.document_version_id: document.supports_critical_claims for document in candidates
        }
        identity = json.dumps({"tenant_id": tenant_id, "ids": ids, "hashes": hashes}, sort_keys=True, default=str)
        manifest_id = f"manifest:{hashlib.sha256(identity.encode()).hexdigest()[:24]}"
        manifest = CorpusManifest(
            manifest_id=manifest_id,
            document_version_ids=list(ids),
            content_hashes=hashes,
            critical_claims_allowed=critical_claims_allowed,
        )
        existing_snapshot = getattr(self.repository, "get_snapshot", lambda _id: None)(manifest_id)
        if existing_snapshot is not None:
            return manifest
        snapshot = CorpusSnapshot(
            snapshot_id=manifest_id,
            tenant_id=tenant_id,
            document_version_ids=ids,
            content_hashes=hashes,
            created_at=self.clock(),
            frozen=True,
        )
        self.repository.save_snapshot(snapshot)
        return manifest

    @staticmethod
    def _document_id(
        work_id: str,
        source_id: str,
        native_id: str,
        version_label: str,
        content_hash: str,
        tenant_id: str | None,
        parser_name: str,
        parser_version: str,
    ) -> str:
        value = "\0".join(
            (
                work_id,
                source_id,
                native_id,
                version_label,
                content_hash,
                tenant_id or "public",
                parser_name,
                parser_version,
            )
        )
        return f"document:{hashlib.sha256(value.encode()).hexdigest()[:32]}"

    def _parse_with_cached_fallback(
        self, content: bytes | str, *, media_type: str
    ) -> tuple[ParsedDocument, ScholarlyParser]:
        """Try parsers in priority order, reusing only a cache entry for a parser that failed."""

        content_hash = _digest(content)
        errors: list[str] = []
        for parser in self.parsers:
            cached = self.repository.find_cached(self.cache_key(content_hash, parser.name, parser.version))
            if cached is not None:
                return (
                    ParsedDocument(
                        text=cached.text,
                        # Document titles can include caller-provided metadata; do not
                        # leak that source-specific value through the shared content cache.
                        title="",
                        abstract=cached.abstract,
                        metadata=cached.metadata,
                    ),
                    parser,
                )
            try:
                return parser.parse(content, media_type=media_type), parser
            except Exception as exc:
                errors.append(f"{parser.name}: {exc}")
        raise RuntimeError("all scholarly parsers failed: " + "; ".join(errors))

    @staticmethod
    def _validate_storage_policy(
        source: SourceDescriptor,
        *,
        tenant_id: str | None,
        content: bytes | str,
        license: str | None,
    ) -> None:
        if source.storage_policy == "link_only" and content:
            raise PermissionError("link_only sources cannot store full text")
        if source.storage_policy != "user_supplied" and not license:
            raise PermissionError("a license is required before storing scholarly content")
        if source.storage_policy == "mirror_allowed" and not CorpusService._redistributable_license(license):
            raise PermissionError("mirror_allowed requires a known redistributable full-text license")
        if source.storage_policy in {"user_supplied", "internal_processing"} and (
            tenant_id is None or not tenant_id.strip()
        ):
            raise PermissionError("private processing sources require tenant isolation")

    @staticmethod
    def _redistributable_license(license: str | None) -> bool:
        if not license:
            return False
        normalized = " ".join(license.casefold().replace("_", "-").split())
        return normalized in {
            "cc0",
            "cc0-1.0",
            "cc-by",
            "cc-by-3.0",
            "cc-by-4.0",
            "cc by 3.0",
            "cc by 4.0",
            "public domain",
            "mit",
            "apache-2.0",
            "apache license 2.0",
            "bsd-2-clause",
            "bsd-3-clause",
            "isc",
        }
