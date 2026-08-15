"""Citation truthfulness verification (verify_citations, task 5, phase 2).

For every critical claim this stage re-fetches the exact source document the
claim cites and programmatically checks whether the evidence quote is really
contained in the source text (DRB FACT / Anthropic CitationAgent style).
Corpus-frozen documents never touch the network; an optional LLM judge can
only downgrade a claim when its quote is absent.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import ConfigDict, Field

from deep_research_agent.connectors.tools.page_fetch import fetch_page
from deep_research_agent.kernel.contracts import ArtifactRef, ClaimRecord, StrictModel

RefetchFn = Callable[[str], dict[str, Any]]
JudgeFn = Callable[[str, str], str | None]


def _default_refetch(url: str) -> dict[str, Any]:
    """Wrap the real network fetch so a verification run can never raise."""

    try:
        result = fetch_page(url)
    except Exception as exc:  # noqa: BLE001 - boundary wrapper, never propagates
        logger.warning("citation refetch failed for {}: {}", url, exc)
        return {"url": url, "final_url": url, "content": "", "fetch_status": "failed"}
    return {
        "url": str(result.get("url") or url),
        "final_url": str(result.get("final_url") or url),
        "content": str(result.get("content") or ""),
        "fetch_status": "ok" if result.get("fetch_status") == "ok" else "failed",
    }


def _token_overlap(claim_text: str, source_text: str) -> float:
    """Deterministic token-overlap ratio over normalized case/punctuation."""

    def tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.casefold()))

    claim_tokens = tokens(claim_text)
    source_tokens = tokens(source_text)
    union = claim_tokens | source_tokens
    if not union:
        return 0.0
    return len(claim_tokens & source_tokens) / len(union)


class CitationVerificationRecord(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verification_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    source_url: str
    document_version_id: str
    method: Literal["deterministic", "llm_judge", "fetch_failed"]
    verdict: Literal["verified", "unsupported", "unverifiable", "fetch_failed"]
    quote_contained: bool
    support_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    fetch_status: Literal["frozen", "ok", "failed", "skipped"]


class CitationVerificationReport(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    items: list[CitationVerificationRecord] = Field(default_factory=list)
    summary: dict[str, int] = Field(
        default_factory=lambda: {
            "total": 0,
            "verified": 0,
            "unsupported": 0,
            "unverifiable": 0,
            "fetch_failed": 0,
        }
    )


class CitationVerifier:
    """Programmatically verify critical claims against their cited sources."""

    def __init__(
        self,
        *,
        refetch: RefetchFn | None = None,
        judge: JudgeFn | None = None,
        max_verifications: int = 8,
    ) -> None:
        self._refetch = refetch or _default_refetch
        self._judge = judge
        self._max_verifications = max_verifications

    def verify(
        self,
        claims: Iterable[ClaimRecord],
        sources: Iterable[ArtifactRef],
        *,
        document_contents: Mapping[str, str] | None = None,
        job_id: str = "unknown",
    ) -> CitationVerificationReport:
        frozen_texts = dict(document_contents or {})
        source_by_document: dict[str, ArtifactRef] = {}
        for source in sorted(sources, key=lambda item: item.artifact_id):
            document_id = source.metadata.get("document_version_id")
            if isinstance(document_id, str):
                source_by_document.setdefault(document_id, source)

        records: list[CitationVerificationRecord] = []
        counts = {
            "total": 0,
            "verified": 0,
            "unsupported": 0,
            "unverifiable": 0,
            "fetch_failed": 0,
        }
        candidates = [claim for claim in claims if claim.critical]
        candidates = sorted(candidates, key=lambda claim: claim.claim_id)
        for claim in candidates[: self._max_verifications]:
            records.append(self._verify_claim(claim, source_by_document, frozen_texts, job_id))
        for record in records:
            counts["total"] += 1
            counts[record.verdict] += 1
        return CitationVerificationReport(
            job_id=job_id,
            items=records,
            summary=counts,
        )

    def _verify_claim(
        self,
        claim: ClaimRecord,
        source_by_document: Mapping[str, ArtifactRef],
        frozen_texts: Mapping[str, str],
        job_id: str,
    ) -> CitationVerificationRecord:
        spans = sorted(claim.evidence_spans, key=lambda span: span.span_id)
        document_version_id = spans[0].document_version_id if spans else ""
        source = source_by_document.get(document_version_id)

        source_url = source.uri if source is not None else ""
        if source is None:
            source_text = ""
            fetch_status: Literal["frozen", "ok", "failed", "skipped"] = "skipped"
        elif document_version_id in frozen_texts:
            source_text = frozen_texts[document_version_id]
            fetch_status = "frozen"
        else:
            fetched = self._refetch(source_url)
            if fetched.get("fetch_status") != "ok":
                source_text = ""
                fetch_status = "failed"
            else:
                source_text = str(fetched.get("content") or "")
                fetch_status = "ok"

        quote_contained = any(span.quote in source_text for span in claim.evidence_spans)
        support_score = _token_overlap(claim.claim, source_text)

        if fetch_status == "failed":
            verdict: Literal["verified", "unsupported", "unverifiable", "fetch_failed"] = (
                "fetch_failed"
            )
            method: Literal["deterministic", "llm_judge", "fetch_failed"] = "fetch_failed"
            rationale = "refetch failed; source text unavailable"
        elif quote_contained:
            verdict = "verified"
            method = "deterministic"
            rationale = "quote contained in source text"
        elif self._judge is not None:
            judged = self._judge(claim.claim, source_text)
            if judged == "verified":
                verdict = "verified"
                method = "llm_judge"
                rationale = "llm judge verdict: verified"
            elif judged in {"unsupported", "contradicted"}:
                verdict = "unsupported"
                method = "llm_judge"
                rationale = f"llm judge verdict: {judged}"
            else:
                verdict = "unverifiable"
                method = "deterministic"
                rationale = "llm judge unavailable; quote absent"
        else:
            verdict = "unverifiable"
            method = "deterministic"
            rationale = (
                "no source artifact for document version"
                if source is None
                else "quote absent and no judge configured"
            )

        return CitationVerificationRecord(
            verification_id=f"{job_id}:verify:{claim.claim_id}",
            claim_id=claim.claim_id,
            claim_text=claim.claim,
            source_url=source_url,
            document_version_id=document_version_id,
            method=method,
            verdict=verdict,
            quote_contained=quote_contained,
            support_score=support_score,
            rationale=rationale,
            fetch_status=fetch_status,
        )

    def to_disk(self, report: CitationVerificationReport, output_dir: Path | str) -> Path:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "citation_verification.json"
        path.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
