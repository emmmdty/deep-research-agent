"""Typed scholarly corpus ingestion and tenant-aware retrieval."""

from .models import (
    CorpusManifest,
    CorpusSnapshot,
    DocumentVersion,
    ParsedDocument,
    SourceDescriptor,
    WorkRecord,
)
from .service import CorpusService
from .storage import InMemoryCorpusRepository

__all__ = [
    "CorpusManifest",
    "CorpusService",
    "CorpusSnapshot",
    "DocumentVersion",
    "InMemoryCorpusRepository",
    "ParsedDocument",
    "SourceDescriptor",
    "WorkRecord",
]
