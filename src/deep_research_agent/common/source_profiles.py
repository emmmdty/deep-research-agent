"""Canonical source-profile names and legacy alias handling."""

from __future__ import annotations


CANONICAL_SOURCE_PROFILES = (
    "company_trusted",
    "company_broad",
    "industry_trusted",
    "industry_broad",
    "public_then_private",
    "trusted_only",
)

LEGACY_SOURCE_PROFILE_ALIASES = {
    "open-web": "company_broad",
    "trusted-web": "company_trusted",
    "public-then-private": "public_then_private",
}

DEFAULT_SOURCE_PROFILE = "company_broad"


def resolve_source_profile_name(profile_name: str | None) -> str:
    """Normalize canonical and legacy source-profile names to the canonical surface."""

    if not profile_name:
        return DEFAULT_SOURCE_PROFILE
    normalized = LEGACY_SOURCE_PROFILE_ALIASES.get(profile_name, profile_name)
    if normalized not in CANONICAL_SOURCE_PROFILES:
        raise ValueError(f"Unsupported source profile: {profile_name}")
    return normalized
