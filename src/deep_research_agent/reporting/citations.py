"""Deterministic inline-citation injection and references rendering.

The report synthesizer is free to write prose; this module is the deterministic
layer that reattaches every claim sentence to the frozen evidence that
supported it. Two mechanisms:

1. Marker pass — the critic writes ``[[claim:<claim_id>]]`` immediately after a
   claim sentence; each marker is validated against the audit outcome and
   replaced with ``[n]`` reference numbers.
2. Verbatim pass — for accepted/qualified claims the synthesizer did not mark,
   the claim sentence is located by normalized substring match and cited the
   same way.

Both passes only ever cite claims whose evidence spans resolve to sources in
the bundle, so citation injection can never fabricate support. A numbered
``References`` section is appended listing every source with a URL; inline
numbers index into that list, mirroring the convention readers expect from
research reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    EvidenceSpan,
)

_MARKER_RE = re.compile(r"\[\[claim:([^\]]+)\]\]")
_REFERENCES_HEADING_RE = re.compile(r"^#{1,6}[ \t]+references[ \t]*$", re.IGNORECASE | re.MULTILINE)
_REGISTER_HEADING_RE = re.compile(r"^#{1,6}[ \t]+claim[ \t]+register[ \t]*$", re.IGNORECASE | re.MULTILINE)
# Minimum normalized claim length before the verbatim matcher will trust a
# substring hit; short phrases match too broadly to be reliable.
_MIN_VERBATIM_CLAIM_CHARS = 24


@dataclass(frozen=True)
class CitationResult:
    """Outcome of one citation-injection pass over a report."""

    markdown: str
    cited_claim_ids: tuple[str, ...] = ()
    marker_cited_claim_ids: tuple[str, ...] = ()
    verbatim_cited_claim_ids: tuple[str, ...] = ()
    dropped_markers: int = 0
    coverage: Mapping[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold().strip()


class CitationInjector:
    """Deterministic citation reattachment for one report bundle."""

    def __init__(
        self,
        *,
        min_verbatim_claim_chars: int = _MIN_VERBATIM_CLAIM_CHARS,
    ) -> None:
        self._min_verbatim_claim_chars = min_verbatim_claim_chars

    def inject(
        self,
        report_markdown: str,
        claims: Iterable[ClaimRecord],
        spans: Iterable[EvidenceSpan],
        sources: Iterable[ArtifactRef],
    ) -> CitationResult:
        del spans  # provenance is carried on the claims themselves
        source_by_document = self._index_sources(sources)
        supported = [claim for claim in claims if claim.support_status in {"accepted", "qualified"}]
        claim_numbers = {
            claim.claim_id: self._claim_source_numbers(claim, source_by_document)
            for claim in supported
        }

        if not source_by_document:
            dropped_markers = len(_MARKER_RE.findall(report_markdown))
            report_markdown = _MARKER_RE.sub("", report_markdown)
            return self._result(report_markdown, set(), set(), set(), dropped_markers, supported)

        cited: set[str] = set()
        marker_cited: set[str] = set()
        dropped_markers = 0

        def replace_marker(match: re.Match[str]) -> str:
            nonlocal dropped_markers
            claim_id = match.group(1)
            numbers = claim_numbers.get(claim_id)
            if not numbers:
                dropped_markers += 1
                return ""
            cited.add(claim_id)
            marker_cited.add(claim_id)
            return _render_marker(numbers)

        report_markdown = _MARKER_RE.sub(replace_marker, report_markdown)
        report_markdown = re.sub(r"[ \t]+\[", " [", report_markdown)

        uncited = [
            claim
            for claim in sorted(supported, key=lambda item: len(item.claim), reverse=True)
            if claim.claim_id not in cited and claim.claim_id in claim_numbers
        ]
        verbatim_cited: set[str] = set()
        if uncited:
            report_markdown, verbatim_cited = self._verbatim_pass(
                report_markdown, uncited, claim_numbers
            )
            cited.update(verbatim_cited)

        report_markdown = self._append_references(report_markdown, source_by_document)
        report_markdown = self._append_claim_register(
            report_markdown, supported, claim_numbers
        )
        return self._result(
            report_markdown, cited, marker_cited, verbatim_cited, dropped_markers, supported
        )

    @staticmethod
    def _result(
        markdown: str,
        cited: set[str],
        marker_cited: set[str],
        verbatim_cited: set[str],
        dropped_markers: int,
        supported: list[ClaimRecord],
    ) -> CitationResult:
        accepted = [claim for claim in supported if claim.support_status == "accepted"]
        qualified = [claim for claim in supported if claim.support_status == "qualified"]
        coverage = {
            "accepted_claim_count": len(accepted),
            "qualified_claim_count": len(qualified),
            "supported_claim_count": len(supported),
            "cited_claim_count": len(cited),
            "cited_in_prose": len(cited),
            "register_entries": len(supported),
            "uncited_claim_count": len(supported) - len(cited),
            "uncited_claim_ids": sorted(
                claim.claim_id for claim in supported if claim.claim_id not in cited
            ),
            "dropped_markers": dropped_markers,
        }
        return CitationResult(
            markdown=markdown,
            cited_claim_ids=tuple(sorted(cited)),
            marker_cited_claim_ids=tuple(sorted(marker_cited)),
            verbatim_cited_claim_ids=tuple(sorted(verbatim_cited)),
            dropped_markers=dropped_markers,
            coverage=coverage,
        )

    @staticmethod
    def _index_sources(sources: Iterable[ArtifactRef]) -> dict[str, tuple[int, ArtifactRef]]:
        ordered = sorted(sources, key=lambda item: item.artifact_id)
        by_document: dict[str, tuple[int, ArtifactRef]] = {}
        for index, source in enumerate(ordered, start=1):
            document_id = source.metadata.get("document_version_id")
            if not isinstance(document_id, str) or not document_id:
                continue
            if document_id not in by_document:
                by_document[document_id] = (index, source)
        return by_document

    @staticmethod
    def _claim_source_numbers(
        claim: ClaimRecord,
        source_by_document: Mapping[str, tuple[int, ArtifactRef]],
    ) -> tuple[int, ...]:
        numbers: set[int] = set()
        for span in claim.evidence_spans:
            entry = source_by_document.get(span.document_version_id)
            if entry is not None:
                numbers.add(entry[0])
        return tuple(sorted(numbers))

    def _verbatim_pass(
        self,
        markdown: str,
        uncited: Iterable[ClaimRecord],
        claim_numbers: Mapping[str, tuple[int, ...]],
    ) -> tuple[str, set[str]]:
        candidates = [
            claim
            for claim in uncited
            if len(_normalize(claim.claim)) >= self._min_verbatim_claim_chars
        ]
        if not candidates:
            return markdown, set()
        pending = [
            (claim.claim_id, _normalize(claim.claim))
            for claim in sorted(candidates, key=lambda item: len(item.claim), reverse=True)
        ]
        cited: set[str] = set()
        cited_sentence_spans: list[tuple[int, int]] = []
        working = markdown
        for claim_id, normalized_claim in pending:
            pattern = re.escape(normalized_claim).replace(r"\ ", r"\s+")
            match = re.search(pattern, working, re.IGNORECASE)
            if match is None:
                continue
            if any(
                span_start < match.end() and match.start() < span_end
                for span_start, span_end in cited_sentence_spans
            ):
                continue
            insertion = _sentence_insertion_point(working, match.end())
            if insertion is None:
                continue
            numbers = claim_numbers[claim_id]
            working = (
                working[:insertion]
                + " "
                + _render_marker(numbers)
                + working[insertion:]
            )
            cited.add(claim_id)
            cited_sentence_spans.append((match.start(), insertion))
        return working, cited

    @staticmethod
    def _append_references(
        markdown: str,
        source_by_document: Mapping[str, tuple[int, ArtifactRef]],
    ) -> str:
        if _REFERENCES_HEADING_RE.search(markdown):
            return markdown
        ordered = sorted(source_by_document.values(), key=lambda item: item[0])
        if not ordered:
            return markdown
        lines = markdown.splitlines()
        if not lines:
            return markdown
        lines.extend(["", "## References", ""])
        for number, source in ordered:
            title = source.metadata.get("source_title") or source.artifact_id
            document_id = source.metadata.get("document_version_id") or ""
            lines.append(f"{number}. {title} — {source.uri} (document: {document_id})")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _append_claim_register(
        markdown: str,
        supported: list[ClaimRecord],
        claim_numbers: Mapping[str, tuple[int, ...]],
    ) -> str:
        """Append the complete evidence register: every supported claim, cited.

        Prose citations attach where the synthesizer marked or verbatim-matched
        a claim; the register is the completeness net — one numbered entry per
        accepted/qualified claim with its source numbers, so every conclusion
        in the bundle is traceable even when prose paraphrases it.
        """
        if not supported or _REGISTER_HEADING_RE.search(markdown):
            return markdown
        lines = markdown.splitlines()
        if not lines:
            return markdown
        lines.extend(["", "## Claim Register", ""])
        for claim in sorted(supported, key=lambda item: item.claim_id):
            numbers = claim_numbers.get(claim.claim_id, ())
            suffix = f" {_render_marker(numbers)}" if numbers else ""
            lines.append(
                f"- ({claim.support_status}, critical={str(claim.critical).lower()}) "
                f"{claim.claim}{suffix}"
            )
        return "\n".join(lines) + "\n"


def _render_marker(numbers: tuple[int, ...]) -> str:
    return "[" + ",".join(str(number) for number in numbers) + "]"


def _sentence_insertion_point(markdown: str, position: int) -> int | None:
    """Index just after the claim sentence ending at ``position``.

    ``position`` is the end offset of the matched claim text. When the claim
    itself ends with a period the citation goes right after it; otherwise the
    next sentence boundary (``.`` followed by space or line end) within a
    bounded window is used. Refuses to insert inside a code fence.
    """
    if position <= 0:
        return None
    if _inside_code_fence(markdown, position):
        return None
    if markdown[position - 1] == ".":
        return position
    window = markdown[position : position + 200]
    boundary = re.search(r"\.(?=[ \n\r\t]|$)", window)
    if boundary is not None:
        insertion = position + boundary.start() + 1
        if not _inside_code_fence(markdown, insertion):
            return insertion
    line_end = markdown.find("\n", position)
    if line_end == -1:
        line_end = len(markdown)
    if markdown[position:line_end].strip() == "" and not _inside_code_fence(markdown, line_end):
        return line_end
    return None


def _inside_code_fence(markdown: str, position: int) -> bool:
    fence_open = False
    offset = 0
    for line in markdown.splitlines(keepends=True):
        if line.startswith("```"):
            fence_open = not fence_open
        offset += len(line)
        if position < offset:
            return fence_open
    return fence_open
