"""Canonical reporting boundary."""

from __future__ import annotations

from .bundle import build_report_bundle, emit_report_artifacts, render_report_html
from .schemas import load_schema, validate_instance

__all__ = [
    "build_report_bundle",
    "emit_report_artifacts",
    "load_schema",
    "render_report_html",
    "validate_instance",
]
