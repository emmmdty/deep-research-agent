"""Canonical connector boundary exposed from the src package."""

from __future__ import annotations

from connectors.registry import ConnectorRegistry, build_connector_registry

__all__ = ["ConnectorRegistry", "build_connector_registry"]
