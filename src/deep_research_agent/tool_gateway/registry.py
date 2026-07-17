"""Protocols and in-memory adapters for the governed tool gateway."""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from deep_research_agent.kernel.contracts import ArtifactRef
from deep_research_agent.tool_gateway.models import (
    ToolHandlerContext,
    ToolResultEnvelope,
    ToolSpec,
)


ToolHandler = Callable[[dict[str, Any], ToolHandlerContext], Any]


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry(Protocol):
    """Tool registration boundary implemented by Task 5 infrastructure."""

    def get(self, name: str) -> RegisteredTool | None: ...


class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool {spec.name!r} is already registered")
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)


class ToolCache(Protocol):
    def get(self, key: str) -> ToolResultEnvelope | None: ...

    def put(self, key: str, value: ToolResultEnvelope, ttl_seconds: float) -> None: ...


class InMemoryToolCache:
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, ToolResultEnvelope]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> ToolResultEnvelope | None:
        now = time.monotonic()
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return value

    def put(self, key: str, value: ToolResultEnvelope, ttl_seconds: float) -> None:
        with self._lock:
            self._values[key] = (time.monotonic() + ttl_seconds, value)


IdempotencyState = Literal["new", "duplicate", "conflict", "pending"]


class IdempotencyStore(Protocol):
    def begin(self, scope: str, key: str, fingerprint: str) -> IdempotencyState: ...

    def complete(
        self,
        scope: str,
        key: str,
        fingerprint: str,
        result: ToolResultEnvelope,
    ) -> None: ...

    def get(self, scope: str, key: str) -> ToolResultEnvelope | None: ...


@dataclass
class _IdempotencyRecord:
    fingerprint: str
    result: ToolResultEnvelope | None = None


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def begin(self, scope: str, key: str, fingerprint: str) -> IdempotencyState:
        record_key = (scope, key)
        with self._lock:
            record = self._records.get(record_key)
            if record is None:
                self._records[record_key] = _IdempotencyRecord(fingerprint=fingerprint)
                return "new"
            if record.fingerprint != fingerprint:
                return "conflict"
            return "duplicate" if record.result is not None else "pending"

    def complete(
        self,
        scope: str,
        key: str,
        fingerprint: str,
        result: ToolResultEnvelope,
    ) -> None:
        record_key = (scope, key)
        with self._lock:
            record = self._records.get(record_key)
            if record is None or record.fingerprint != fingerprint:
                raise RuntimeError("idempotency claim changed during invocation")
            record.result = result

    def get(self, scope: str, key: str) -> ToolResultEnvelope | None:
        with self._lock:
            record = self._records.get((scope, key))
            return record.result if record is not None else None


class BudgetStore(Protocol):
    def consume(self, tenant_id: str, job_id: str, task_id: str, limit: int) -> bool: ...


class InMemoryBudgetStore:
    def __init__(self) -> None:
        self._usage: dict[tuple[str, str, str], int] = {}
        self._lock = threading.Lock()

    def consume(self, tenant_id: str, job_id: str, task_id: str, limit: int) -> bool:
        key = (tenant_id, job_id, task_id)
        with self._lock:
            used = self._usage.get(key, 0)
            if used >= limit:
                return False
            self._usage[key] = used + 1
            return True

    def used(self, tenant_id: str, job_id: str, task_id: str) -> int:
        with self._lock:
            return self._usage.get((tenant_id, job_id, task_id), 0)


class ArtifactStore(Protocol):
    def write(
        self,
        content: bytes,
        *,
        media_type: str,
        task_id: str,
    ) -> ArtifactRef: ...


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, bytes] = {}

    def write(
        self,
        content: bytes,
        *,
        media_type: str,
        task_id: str,
    ) -> ArtifactRef:
        digest = hashlib.sha256(content).hexdigest()
        artifact_id = f"tool-result:{digest}"
        self._artifacts[artifact_id] = bytes(content)
        return ArtifactRef(
            artifact_id=artifact_id,
            uri=f"memory://{artifact_id}",
            media_type=media_type,
            content_sha256=digest,
            created_by_task_id=task_id,
            metadata={"trust": "untrusted"},
        )

    def read(self, artifact_id: str) -> bytes:
        return self._artifacts[artifact_id]
