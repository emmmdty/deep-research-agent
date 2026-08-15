"""Deterministic policy decisions for memory retention and sensitive writes."""

from __future__ import annotations

from datetime import timedelta

from .models import MemoryScope, Sensitivity

DEFAULT_TTL_SECONDS: dict[MemoryScope, int] = {
    MemoryScope.RUN_STATE: 60 * 60,
    MemoryScope.CONVERSATION_FOCUS: 24 * 60 * 60,
    MemoryScope.USER_MEMORY: 365 * 24 * 60 * 60,
    MemoryScope.TOPIC_MEMORY: 30 * 24 * 60 * 60,
    MemoryScope.AGENT_EXPERIENCE: 180 * 24 * 60 * 60,
}


class MemoryPolicy:
    def __init__(self, *, default_ttls: dict[MemoryScope, int] | None = None) -> None:
        self.default_ttls = {**DEFAULT_TTL_SECONDS, **(default_ttls or {})}

    def requires_confirmation(self, sensitivity: Sensitivity | str) -> bool:
        return Sensitivity(sensitivity) in {Sensitivity.SENSITIVE, Sensitivity.RESTRICTED}

    def ttl(self, scope: MemoryScope | str, ttl_seconds: int | float | None) -> timedelta | None:
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                raise ValueError("memory TTL must be positive")
            return timedelta(seconds=ttl_seconds)
        return timedelta(seconds=self.default_ttls[MemoryScope(scope)])

    def authorize_write(self, sensitivity: Sensitivity | str, *, confirmed: bool) -> None:
        if self.requires_confirmation(sensitivity) and not confirmed:
            raise PermissionError("sensitive memory writes require explicit confirmation")
