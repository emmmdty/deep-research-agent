"""Cross-job memory reuse: verified-source recall and post-job harvest (T14).

Two cooperating pieces sit on top of the tenant-isolated ``MemoryService``:

* ``MemoryRecall`` — the researcher's front-door: given the task objective
  and the just-planned queries it looks up previously settled verified
  sources (``MemoryScope.TOPIC_MEMORY``) and reports which planned queries
  are already covered. A cross-tenant search (``PermissionError``) is treated
  as a no-hit so recall can never break live gathering.
* ``MemoryHarvester`` — the job-level writer: after a completed scheduler-v2
  job it settles every source that (a) carries at least one claim whose
  evidence-span quote is verbatim contained in the source text AND (b) whose
  claim carries a ``verified`` citation-verification verdict. Without
  citation-verification data nothing is harvested, and harvesting never
  re-verifies (no network, no judge — only the frozen corpus is inspected).

Record addressing is deterministic: ``subject_id`` is ``tenant:{tenant_id}``
and the record ``key`` is ``source:{topic}:{url}``, so re-harvesting the same
source writes the same key and ``MemoryService.write`` returns the existing
ACTIVE record (idempotency); a changed source supersedes the old record.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from deep_research_agent.kernel.contracts import ArtifactRef, ClaimRecord
from deep_research_agent.memory_v2.models import MemoryRecord, MemoryScope
from deep_research_agent.memory_v2.service import InMemoryMemoryRepository, MemoryService

_RECALL_MAX_TERMS = 5
_RECALL_MIN_TERM_LENGTH = 4
_RECALL_STOPWORDS = frozenset(
    {
        "about",
        "across",
        "after",
        "based",
        "between",
        "could",
        "does",
        "from",
        "into",
        "more",
        "most",
        "other",
        "should",
        "state",
        "their",
        "there",
        "these",
        "they",
        "this",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
    }
)
_SUBJECT_PREFIX = "tenant:"
_MEMORY_KEY_PREFIX = "source:"


def subject_id_for_tenant(tenant_id: str) -> str:
    """Deterministic subject id for topic memory: ``tenant:{tenant_id}``."""

    return f"{_SUBJECT_PREFIX}{tenant_id}"


def memory_key_for_source(topic: str, url: str) -> str:
    """Deterministic per-(topic, url) memory key; tenant scopes the namespace."""

    return f"{_MEMORY_KEY_PREFIX}{topic}:{url}"


def _query_terms(objective: str) -> list[str]:
    """Deterministic keyword extraction from an objective.

    Keeps only alphanumeric words of at least ``_RECALL_MIN_TERM_LENGTH``
    characters, minus a small English stoplist, deduplicated and capped so
    ``MemoryService.search`` (every term must match) stays selective.
    """

    terms: list[str] = []
    seen: set[str] = set()
    for match in re.findall(r"[a-zA-Z0-9]+", objective):
        word = match.casefold()
        if len(word) < _RECALL_MIN_TERM_LENGTH or word in _RECALL_STOPWORDS:
            continue
        if word in seen:
            continue
        seen.add(word)
        terms.append(word)
        if len(terms) >= _RECALL_MAX_TERMS:
            break
    return terms


def _source_from_record(record: MemoryRecord) -> dict[str, Any] | None:
    """Rebuild a researcher-shaped source dict from a topic-memory record.

    The record content is the JSON of exactly ``{"url","snippet","title",
    "tool","kind"}`` (harvested verbatim from a real run), so recalled
    sources flow through corpus hashing, quote containment and the audit gate
    byte-identically to live-search results. Provenance metadata is attached
    under ``_memory`` and never leaks into artifacts.
    """

    try:
        payload = json.loads(record.content)
    except Exception:  # noqa: BLE001 - corrupt records are no-hits
        return None
    if not isinstance(payload, dict):
        return None
    url = str(payload.get("url") or "")
    snippet = str(payload.get("snippet") or "")
    if not url or not snippet:
        return None
    source = {
        "url": url,
        "snippet": snippet,
        "title": str(payload.get("title") or url),
        "tool": str(payload.get("tool") or "web_search"),
        "kind": str(payload.get("kind") or "snippet"),
    }
    source["_memory"] = {
        "memory_id": record.memory_id,
        "job_id": str(record.provenance.get("job_id") or ""),
        "claim_ids": record.provenance.get("claim_ids") or [],
        "verdict": str(record.provenance.get("verdict") or ""),
        "quote": str(record.provenance.get("quote") or ""),
        "document_version_id": str(record.provenance.get("document_version_id") or ""),
        "harvested_at": record.created_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }
    return source


def _query_covered(
    query: dict[str, str], recalled: list[tuple[dict[str, Any], MemoryRecord]], recalled_urls: set[str]
) -> bool:
    """Deterministic URL-based coverage: was this planned query answered before?

    A planned query is covered when some recalled record's ``query_urls``
    metadata holds an entry with the same (query, tool) whose recorded URL
    set overlaps the recalled source URLs. Records written without
    ``query_urls`` cover nothing.
    """

    for _, record in recalled:
        entries = record.metadata.get("query_urls")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("query") or "") != str(query.get("query") or ""):
                continue
            if str(entry.get("tool") or "") != str(query.get("tool") or ""):
                continue
            urls = entry.get("urls")
            if not isinstance(urls, list):
                continue
            if any(str(url) in recalled_urls for url in urls):
                return True
    return False


def _normalize_query_results(query_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize the researcher's per-query URL report for memory metadata."""

    normalized: list[dict[str, Any]] = []
    for item in query_results:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query") or "")
        tool = str(item.get("tool") or "")
        urls = item.get("urls")
        if not query or not tool:
            continue
        normalized.append(
            {
                "query": query,
                "tool": tool,
                "urls": [str(url) for url in urls] if isinstance(urls, list) else [],
            }
        )
    return normalized


class MemoryRecall:
    """Researcher-facing recall over previously settled verified sources.

    Threaded through ``TaskExecutionContext.memory`` (and therefore the
    scheduler), recall is consulted in ``_gather_queries`` before any tool
    invocation: hits inject the recalled sources first (deduped, counted
    against the researcher's source cap) and skip covered queries.
    """

    def __init__(self, memory_service: MemoryService) -> None:
        self.memory_service = memory_service

    def recall(
        self,
        objective: str,
        planned_queries: list[dict[str, str]],
        *,
        tenant_id: str,
    ) -> tuple[list[dict[str, Any]], set[int]]:
        """Return (recalled source dicts, covered planned-query indices).

        Empty objective terms, empty memory, or a cross-tenant search denial
        all resolve to a no-hit so live gathering is never perturbed.
        """

        terms = _query_terms(objective)
        if not terms:
            return [], set()
        try:
            records = self.memory_service.search(
                " ".join(terms),
                tenant_id=tenant_id,
                scope=MemoryScope.TOPIC_MEMORY,
            )
        except PermissionError:
            logger.warning(
                "memory recall denied for tenant {}; treating as no-hit", tenant_id
            )
            return [], set()
        recalled: list[tuple[dict[str, Any], MemoryRecord]] = []
        for record in records:
            source = _source_from_record(record)
            if source is not None:
                recalled.append((source, record))
        recalled_urls = {str(source["url"]) for source, _ in recalled}
        covered = {
            index
            for index, query in enumerate(planned_queries)
            if _query_covered(query, recalled, recalled_urls)
        }
        return [source for source, _ in recalled], covered


class MemoryHarvester:
    """Settle verified sources into TOPIC_MEMORY after a completed job.

    Verified (deterministic, documented): a source is harvestable iff at
    least one of its claims has an evidence-span quote verbatim contained in
    the source text AND, when citation-verification data is provided, that
    claim's verdict is ``verified``. Without citation-verification data
    nothing is harvested. Harvesting never re-verifies: it only inspects the
    frozen corpus and the verification report already produced by the job.
    """

    def __init__(self, memory_service: MemoryService) -> None:
        self.memory_service = memory_service

    def harvest(
        self,
        *,
        tenant_id: str,
        topic: str,
        claims: list[ClaimRecord],
        artifacts: list[ArtifactRef],
        citation_verification: dict[str, Any],
        query_results: list[dict[str, Any]] | None = None,
        job_id: str,
        ttl_seconds: int | float | None = None,
    ) -> list[MemoryRecord]:
        if not isinstance(citation_verification, dict):
            return []
        items = citation_verification.get("items")
        if not isinstance(items, list) or not items:
            return []
        verified_claim_ids = {
            str(item["claim_id"])
            for item in items
            if isinstance(item, dict) and str(item.get("verdict") or "") == "verified"
        }
        if not verified_claim_ids:
            return []
        normalized_queries = _normalize_query_results(query_results or [])
        written: list[MemoryRecord] = []
        for artifact in artifacts:
            document_version_id = artifact.metadata.get("document_version_id")
            source_text = artifact.metadata.get("source_text")
            if not isinstance(document_version_id, str) or not isinstance(source_text, str):
                continue
            grounded = [
                claim
                for claim in claims
                if claim.claim_id in verified_claim_ids
                and any(
                    span.document_version_id == document_version_id and span.quote in source_text
                    for span in claim.evidence_spans
                )
            ]
            if not grounded:
                continue
            source = {
                "url": artifact.uri,
                "snippet": source_text,
                "title": str(artifact.metadata.get("source_title") or artifact.uri),
                "tool": str(artifact.metadata.get("tool") or ""),
                "kind": str(artifact.metadata.get("source_kind") or "snippet"),
            }
            quote = next(
                span.quote
                for claim in grounded
                for span in claim.evidence_spans
                if span.document_version_id == document_version_id and span.quote in source_text
            )
            record = self.memory_service.write(
                tenant_id=tenant_id,
                subject_id=subject_id_for_tenant(tenant_id),
                scope=MemoryScope.TOPIC_MEMORY,
                key=memory_key_for_source(topic, artifact.uri),
                content=json.dumps(source, ensure_ascii=True, sort_keys=True),
                provenance={
                    "job_id": job_id,
                    "claim_ids": sorted({claim.claim_id for claim in grounded}),
                    "verdict": "verified",
                    "quote": quote,
                    "document_version_id": document_version_id,
                },
                ttl_seconds=ttl_seconds,
                metadata={"query_urls": normalized_queries},
            )
            written.append(record)
        return written


_process_memory: MemoryRecall | None = None


def process_memory_recall() -> MemoryRecall:
    """Process-wide shared recall over the default in-memory topic memory.

    Schedulers built by the composition root share this instance so jobs in
    one process genuinely reuse each other's settled sources (cross-job
    memory reuse) without any configuration surface.
    """

    global _process_memory
    if _process_memory is None:
        _process_memory = MemoryRecall(MemoryService(repository=InMemoryMemoryRepository()))
    return _process_memory
