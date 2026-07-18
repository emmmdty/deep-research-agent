"""Contracts for governed memory writes and reads."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryScope(str, Enum):
    RUN_STATE = "run_state"
    CONVERSATION_FOCUS = "conversation_focus"
    USER_MEMORY = "user_memory"
    TOPIC_MEMORY = "topic_memory"
    AGENT_EXPERIENCE = "agent_experience"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    DELETED = "deleted"
    PENDING_CONFIRMATION = "pending_confirmation"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    scope: MemoryScope
    key: str = Field(min_length=1)
    content: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    supersedes: str | None = None
    superseded_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= now
