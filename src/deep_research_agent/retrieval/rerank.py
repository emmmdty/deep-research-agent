"""Semantic retrieval primitives for the evidence-first runtime.

The agent's search path is governed and discovery-oriented; this module adds an
optional semantic layer (embedding similarity) used to re-rank candidate sources
before full-page reads, so the model's page selection is informed by relevance
to the task objective.

Embeddings are produced locally (ONNX via ``fastembed``) and loaded lazily on
first use; every entry point degrades gracefully when the optional dependency
or model download is unavailable, so the runtime keeps working without it.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Sequence

from loguru import logger

_DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingProvider:
    """Local embedding provider (lazy-loaded fastembed / ONNX)."""

    def __init__(self, model_name: str | None = None, *, cache_dir: str | None = None) -> None:
        self._model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL
        )
        self._cache_dir = cache_dir or os.environ.get("EMBEDDING_CACHE_DIR")
        self._model: Any | None = None

    @property
    def available(self) -> bool:
        try:
            self._lazy_load()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("embedding provider unavailable: {}", exc)
            return False

    def _lazy_load(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding  # optional dependency

            kwargs: dict[str, Any] = {"model_name": self._model_name}
            if self._cache_dir:
                kwargs["cache_dir"] = self._cache_dir
            self._model = TextEmbedding(**kwargs)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts; returns normalized vectors."""
        model = self._lazy_load()
        vectors: list[list[float]] = []
        for vector in model.embed(list(texts)):
            values = [float(value) for value in vector]
            vectors.append(_l2_normalize(values))
        return vectors

    def embed_one(self, text: str) -> list[float]:
        vectors = self.embed([text])
        return vectors[0] if vectors else []


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity of two vectors (assumes L2-normalized inputs)."""
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


@dataclass(frozen=True)
class RankedSource:
    """A source with its semantic relevance score."""

    index: int
    relevance: float


class SemanticReranker:
    """Rank candidate sources by semantic relevance to a query/objective."""

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self._provider = provider or EmbeddingProvider()

    @property
    def available(self) -> bool:
        return self._provider.available

    def rank(
        self,
        query: str,
        candidate_texts: Sequence[str],
    ) -> list[RankedSource]:
        """Rank 1-based candidate positions by relevance to ``query``.

        Returns ``RankedSource`` entries sorted by descending relevance; the
        ``index`` field is the 1-based position in ``candidate_texts`` (the
        same numbering claims use), so re-ranking never renumbers sources.
        """

        if not candidate_texts:
            return []
        if not self.available or not query.strip():
            return [RankedSource(index=position, relevance=0.0) for position in range(1, len(candidate_texts) + 1)]
        try:
            query_vector = self._provider.embed_one(query)
            vectors = self._provider.embed(candidate_texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("semantic rerank failed; falling back to original order: {}", exc)
            return [RankedSource(index=position, relevance=0.0) for position in range(1, len(candidate_texts) + 1)]
        scored = [
            RankedSource(index=position, relevance=cosine_similarity(query_vector, vector))
            for position, vector in enumerate(vectors, start=1)
        ]
        return sorted(scored, key=lambda item: item.relevance, reverse=True)


__all__ = [
    "EmbeddingProvider",
    "RankedSource",
    "SemanticReranker",
    "cosine_similarity",
]
