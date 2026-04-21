"""Canonical connector boundary."""

from __future__ import annotations

from .files import LocalFileIngestor
from .legacy import LegacyConnectorAdapter
from .models import ConnectorCandidate, ConnectorFetchResult, ConnectorHealthRecord
from .registry import ConnectorRegistry, build_connector_registry
from .snapshot_store import SnapshotInput, SnapshotManifest, SnapshotStore
from .utils import canonicalize_uri, domain_from_uri, fetch_uri_block_reason

__all__ = [
    "ConnectorCandidate",
    "ConnectorFetchResult",
    "ConnectorHealthRecord",
    "ConnectorRegistry",
    "LegacyConnectorAdapter",
    "LocalFileIngestor",
    "SnapshotInput",
    "SnapshotManifest",
    "SnapshotStore",
    "build_connector_registry",
    "canonicalize_uri",
    "domain_from_uri",
    "fetch_uri_block_reason",
]
