"""Phase 03 connectors 统一入口。"""

from .legacy import LegacyConnectorAdapter
from .models import ConnectorCandidate, ConnectorFetchResult, ConnectorHealthRecord
from .registry import ConnectorRegistry, build_connector_registry
from .snapshot_store import SnapshotInput, SnapshotManifest, SnapshotStore

__all__ = [
    "ConnectorCandidate",
    "ConnectorFetchResult",
    "ConnectorHealthRecord",
    "ConnectorRegistry",
    "LegacyConnectorAdapter",
    "SnapshotInput",
    "SnapshotManifest",
    "SnapshotStore",
    "build_connector_registry",
]
