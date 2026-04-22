"""Shared integrity and capability guard helpers."""

from __future__ import annotations

from pathlib import Path


def redact_query(query: str, denylist_terms: list[str]) -> str:
    """Redact denylisted benchmark-material terms from a query string."""

    redacted = query
    for term in denylist_terms:
        redacted = redacted.replace(term, "[REDACTED]")
    return redacted


def detect_denylist_hits(query: str, denylist_terms: list[str]) -> list[str]:
    """Return denylist hits found in a query."""

    normalized = query.lower()
    return [term for term in denylist_terms if term.lower() in normalized]


def detect_canary(query: str, canary_terms: list[str]) -> list[str]:
    """Return canary strings found in a query."""

    normalized = query.lower()
    return [term for term in canary_terms if term.lower() in normalized]


def sanitize_attachment_paths(paths: list[str]) -> list[str]:
    """Normalize attachment references to repo-safe basenames."""

    return [Path(path).name for path in paths]
