"""Tenant-isolated memory repository and service."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime
from typing import Protocol

from .models import MemoryRecord, MemoryScope, MemoryStatus, Sensitivity, utc_now
from .policy import MemoryPolicy


class MemoryRepository(Protocol):
    def save(self, record: MemoryRecord) -> None: ...

    def get(self, memory_id: str) -> MemoryRecord | None: ...

    def list(self, *, tenant_id: str | None = None, subject_id: str | None = None) -> list[MemoryRecord]: ...


class SQLMemoryRepository(Protocol):
    """Production SQL boundary reserved for Task 5."""

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> object: ...


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self.records: dict[str, MemoryRecord] = {}

    def save(self, record: MemoryRecord) -> None:
        existing = self.records.get(record.memory_id)
        if existing is not None and existing != record:
            immutable_fields = (
                "tenant_id",
                "subject_id",
                "scope",
                "key",
                "content",
                "provenance",
                "confidence",
                "sensitivity",
                "created_at",
                "expires_at",
                "supersedes",
                "metadata",
            )
            if any(getattr(existing, field) != getattr(record, field) for field in immutable_fields):
                raise ValueError(f"memory record {record.memory_id!r} is immutable")
        self.records[record.memory_id] = deepcopy(record)

    def get(self, memory_id: str) -> MemoryRecord | None:
        record = self.records.get(memory_id)
        return deepcopy(record) if record is not None else None

    def list(self, *, tenant_id: str | None = None, subject_id: str | None = None) -> list[MemoryRecord]:
        return deepcopy([
            record
            for record in self.records.values()
            if (tenant_id is None or record.tenant_id == tenant_id)
            and (subject_id is None or record.subject_id == subject_id)
        ])


class MemoryService:
    def __init__(
        self,
        *,
        repository: MemoryRepository | None = None,
        policy: MemoryPolicy | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.repository = repository or InMemoryMemoryRepository()
        self.policy = policy or MemoryPolicy()
        self.clock = clock

    def write(
        self,
        *,
        tenant_id: str,
        subject_id: str | None = None,
        user_id: str | None = None,
        scope: MemoryScope | str,
        key: str,
        content: str,
        provenance: dict[str, object] | None = None,
        confidence: float = 1.0,
        sensitivity: Sensitivity | str = Sensitivity.INTERNAL,
        ttl_seconds: int | float | None = None,
        confirmed: bool = False,
        supersedes: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MemoryRecord:
        subject = subject_id or user_id
        if not subject or not subject.strip():
            raise ValueError("subject_id is required")
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        normalized_scope = MemoryScope(scope)
        normalized_sensitivity = Sensitivity(sensitivity)
        self.policy.authorize_write(normalized_sensitivity, confirmed=confirmed)
        now = self.clock()
        expiry_delta = self.policy.ttl(normalized_scope, ttl_seconds)
        expires_at = now + expiry_delta if expiry_delta is not None else None
        existing = self._active_for_key(tenant_id, subject, normalized_scope, key, now)
        explicit_target = None
        if supersedes is not None:
            explicit_target = self.repository.get(supersedes)
            if explicit_target is None:
                raise KeyError(f"unknown superseded memory record {supersedes!r}")
            if (
                explicit_target.tenant_id != tenant_id
                or explicit_target.subject_id != subject
                or explicit_target.scope != normalized_scope
                or explicit_target.key != key
            ):
                raise PermissionError("a memory may only supersede the same key in the same tenant scope")
            explicit_target = self._fresh(explicit_target)
            if explicit_target.status != MemoryStatus.ACTIVE:
                raise ValueError("only an active memory record can be superseded")
        memory_id = self._memory_id(tenant_id, subject, normalized_scope, key, content, now)
        record = MemoryRecord(
            memory_id=memory_id,
            tenant_id=tenant_id,
            subject_id=subject,
            scope=normalized_scope,
            key=key,
            content=content,
            provenance=dict(provenance or {}),
            confidence=confidence,
            sensitivity=normalized_sensitivity,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            supersedes=(explicit_target.memory_id if explicit_target is not None else existing.memory_id if existing else None),
            metadata=dict(metadata or {}),
        )
        if existing is not None and existing.content == content:
            return existing
        if existing is not None:
            self.repository.save(existing.model_copy(update={"status": MemoryStatus.SUPERSEDED, "superseded_by": memory_id, "updated_at": now}))
        if explicit_target is not None and (existing is None or explicit_target.memory_id != existing.memory_id):
            self.repository.save(
                explicit_target.model_copy(
                    update={"status": MemoryStatus.SUPERSEDED, "superseded_by": memory_id, "updated_at": now}
                )
            )
        self.repository.save(record)
        return self.repository.get(record.memory_id) or record

    def get(self, memory_id: str, *, tenant_id: str) -> MemoryRecord:
        record = self.repository.get(memory_id)
        if record is None:
            raise KeyError(f"unknown memory record {memory_id!r}")
        if record.tenant_id != tenant_id:
            raise PermissionError("memory record is outside the authorized tenant")
        return self._fresh(record)

    def search(self, query: str, *, tenant_id: str, scope: MemoryScope | str | None = None) -> list[MemoryRecord]:
        terms = [part for part in query.casefold().split() if part]
        normalized_scope = MemoryScope(scope) if scope is not None else None
        matches: list[MemoryRecord] = []
        foreign_match = False
        for record in self.repository.list():
            haystack = f"{record.key} {record.content}".casefold()
            if terms and not all(term in haystack for term in terms):
                continue
            if normalized_scope is not None and record.scope != normalized_scope:
                continue
            if record.tenant_id != tenant_id:
                foreign_match = True
                continue
            current = self._fresh(record)
            if current.status == MemoryStatus.ACTIVE:
                matches.append(current)
        if foreign_match:
            raise PermissionError("cross-tenant memory search is denied")
        return sorted(matches, key=lambda item: item.created_at)

    def delete_user(self, subject_id: str, *, tenant_id: str) -> int:
        count = 0
        now = self.clock()
        for record in self.repository.list(tenant_id=tenant_id, subject_id=subject_id):
            if record.status != MemoryStatus.DELETED:
                self.repository.save(record.model_copy(update={"status": MemoryStatus.DELETED, "updated_at": now}))
                count += 1
        return count

    def export_user(self, subject_id: str, *, tenant_id: str) -> list[MemoryRecord]:
        records = []
        for record in self.repository.list(tenant_id=tenant_id, subject_id=subject_id):
            current = self._fresh(record)
            if current.status not in {MemoryStatus.DELETED, MemoryStatus.EXPIRED}:
                records.append(current)
        return sorted(records, key=lambda item: item.created_at)

    def export(self, subject_id: str, *, tenant_id: str) -> list[MemoryRecord]:
        return self.export_user(subject_id, tenant_id=tenant_id)

    def expire(self) -> int:
        count = 0
        now = self.clock()
        for record in self.repository.list():
            if record.status == MemoryStatus.ACTIVE and record.is_expired(now):
                self.repository.save(record.model_copy(update={"status": MemoryStatus.EXPIRED, "updated_at": now}))
                count += 1
        return count

    def read(self, memory_id: str, *, tenant_id: str) -> MemoryRecord:
        """Alias used by repository-facing callers."""

        return self.get(memory_id, tenant_id=tenant_id)

    def delete(self, memory_id: str, *, tenant_id: str) -> bool:
        record = self.get(memory_id, tenant_id=tenant_id)
        if record.status == MemoryStatus.DELETED:
            return False
        self.repository.save(record.model_copy(update={"status": MemoryStatus.DELETED, "updated_at": self.clock()}))
        return True

    def _fresh(self, record: MemoryRecord) -> MemoryRecord:
        if record.status == MemoryStatus.ACTIVE and record.is_expired(self.clock()):
            expired = record.model_copy(update={"status": MemoryStatus.EXPIRED, "updated_at": self.clock()})
            self.repository.save(expired)
            return expired
        return record

    def _active_for_key(
        self, tenant_id: str, subject_id: str, scope: MemoryScope, key: str, now: datetime
    ) -> MemoryRecord | None:
        for record in self.repository.list(tenant_id=tenant_id, subject_id=subject_id):
            if record.scope == scope and record.key == key:
                current = self._fresh(record)
                if current.status == MemoryStatus.ACTIVE and not current.is_expired(now):
                    return current
        return None

    @staticmethod
    def _memory_id(
        tenant_id: str,
        subject_id: str,
        scope: MemoryScope,
        key: str,
        content: str,
        now: datetime,
    ) -> str:
        value = "\0".join((tenant_id, subject_id, scope.value, key, content, now.isoformat()))
        return f"memory:{hashlib.sha256(value.encode()).hexdigest()[:32]}"
