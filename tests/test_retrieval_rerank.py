"""Tests for the semantic retrieval / rerank layer.

The reranker is exercised with a deterministic fake provider (no model
downloads); one optional real-model smoke is gated behind an env flag.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.retrieval.rerank import (
    EmbeddingProvider,
    SemanticReranker,
    cosine_similarity,
)


class FakeEmbeddingProvider:
    """Deterministic keyword-hash embeddings (no downloads, no network)."""

    @property
    def available(self) -> bool:
        return True

    def embed(self, texts):
        return [_hash_vector(text) for text in texts]

    def embed_one(self, text):
        return _hash_vector(text)


def _hash_vector(text: str) -> list[float]:
    """Deterministic keyword-hash embeddings (stable across processes)."""
    import hashlib

    vector = [0.0] * 256
    for token in text.lower().split():
        digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        vector[digest % 256] += 1.0
    norm = sum(v * v for v in vector) ** 0.5
    return [v / norm if norm else 0.0 for v in vector]


def _snippet(index: int, text: str) -> dict:
    return {
        "index": index,
        "kind": "snippet",
        "tool": "web_search",
        "title": f"source-{index}",
        "url": f"https://example.com/{index}",
        "snippet": text,
    }


def _fake_reranker() -> SemanticReranker:
    reranker = SemanticReranker(provider=FakeEmbeddingProvider())  # type: ignore[arg-type]
    reranker.available = True  # fake provider reports available
    return reranker


# ------------------------------------------------------------------ unit


def test_cosine_similarity():
    left = _hash_vector("agent tools memory")
    right = _hash_vector("agent tools memory")
    other = _hash_vector("quantum physics equations")
    assert cosine_similarity(left, right) > 0.99
    assert cosine_similarity(left, other) < 0.9
    assert cosine_similarity([], [1.0]) == 0.0


def test_reranker_ranks_relevant_first():
    reranker = SemanticReranker(provider=FakeEmbeddingProvider())  # type: ignore[arg-type]
    ranked = reranker.rank(
        "agents use tools and memory in 2026",
        [
            "quantum physics and equations of motion",
            "multi-agent systems with tools and memory",
            "cooking recipes for pasta",
        ],
    )
    assert ranked[0].index == 2
    assert ranked[0].relevance > ranked[1].relevance


def test_reranker_keeps_one_based_indices():
    reranker = SemanticReranker(provider=FakeEmbeddingProvider())  # type: ignore[arg-type]
    ranked = reranker.rank("unrelated query", ["a", "b", "c"])
    assert {entry.index for entry in ranked} == {1, 2, 3}


def test_reranker_falls_back_without_provider():
    class BrokenProvider:
        @property
        def available(self) -> bool:
            return False

        def embed_one(self, text):
            raise RuntimeError("no model")

        def embed(self, texts):
            raise RuntimeError("no model")

    reranker = SemanticReranker(provider=BrokenProvider())  # type: ignore[arg-type]
    ranked = reranker.rank("query", ["x", "y"])
    assert [entry.relevance for entry in ranked] == [0.0, 0.0]


# ------------------------------------------------------------- integration


def test_reranked_source_list_orders_by_relevance_and_keeps_labels():
    import os

    os.environ["EMBEDDINGS_ENABLED"] = "true"
    try:
        reranker = SemanticReranker(provider=FakeEmbeddingProvider())  # type: ignore[arg-type]
        sources = [
            _snippet(1, "quantum physics and equations of motion"),
            _snippet(2, "multi-agent systems with tools and memory"),
            _snippet(3, "cooking recipes for pasta"),
        ]
        stats: dict = {}
        worker = LLMResearcherWorker()
        with patch.object(
            LLMResearcherWorker,
            "_semantic_reranker",
            staticmethod(lambda: reranker),
        ):
            digest = worker._reranked_source_list(
                "agents use tools and memory in 2026", sources, max_chars=200, stats=stats
            )
    finally:
        os.environ.pop("EMBEDDINGS_ENABLED", None)
    assert stats["rerank_available"] is True
    assert digest.index("[2]") < digest.index("[1]") < digest.index("[3]")
    assert "relevance" in digest
    assert "<source_data>" in digest and "</source_data>" in digest


def test_reranked_source_list_falls_back_to_original_order():
    worker = LLMResearcherWorker()
    sources = [_snippet(1, "a"), _snippet(2, "b")]
    stats: dict = {}
    with patch.object(LLMResearcherWorker, "_semantic_reranker", staticmethod(lambda: None)):
        digest = worker._reranked_source_list("q", sources, max_chars=200, stats=stats)
    assert stats["rerank_available"] is False
    assert digest.index("[1]") < digest.index("[2]")
    assert "relevance" not in digest


@pytest.mark.skipif(
    not os.environ.get("RUN_EMBEDDING_SMOKE"),
    reason="real embedding model smoke requires RUN_EMBEDDING_SMOKE=1",
)
def test_real_embedding_smoke():
    """One real-model smoke: relevant pair scores above an irrelevant pair."""
    provider = EmbeddingProvider()
    assert provider.available
    reranker = SemanticReranker(provider=provider)
    ranked = reranker.rank(
        "agents use tools and memory",
        ["agents use tools and memory in 2026", "quantum physics equations"],
    )
    assert ranked[0].index == 1
    assert ranked[0].relevance > ranked[1].relevance
