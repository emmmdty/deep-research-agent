"""Common contracts shared across the canonical package."""

from __future__ import annotations

from deep_research_agent.common.source_profiles import (
    CANONICAL_SOURCE_PROFILES,
    DEFAULT_SOURCE_PROFILE,
    LEGACY_SOURCE_PROFILE_ALIASES,
    resolve_source_profile_name,
)

__all__ = [
    "CANONICAL_SOURCE_PROFILES",
    "DEFAULT_SOURCE_PROFILE",
    "LEGACY_SOURCE_PROFILE_ALIASES",
    "resolve_source_profile_name",
]
