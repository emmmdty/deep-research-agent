"""Deterministic inline-citation injection tests."""

from __future__ import annotations


from deep_research_agent.kernel.contracts import ArtifactRef, ClaimRecord, EvidenceSpan
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2
from deep_research_agent.reporting.citations import CitationInjector


DOC_A = "a" * 64
DOC_B = "b" * 64


def _source(artifact_id: str, document_id: str, *, title: str | None = None) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        uri=f"https://example.com/{artifact_id}",
        media_type="text/markdown",
        content_sha256=DOC_A if document_id == "doc-a" else DOC_B,
        created_by_task_id="research-1",
        metadata={
            "document_version_id": document_id,
            "source_title": title or f"Title {artifact_id}",
            "tool": "web_search",
        },
    )


def _span(span_id: str, document_id: str = "doc-a", quote: str = "The system improved recall by 4.2 points.") -> EvidenceSpan:
    return EvidenceSpan(
        span_id=span_id,
        document_version_id=document_id,
        section="1.1 Findings",
        quote=quote,
        extraction_method="agent_grounding",
    )


def _claim(
    claim_id: str,
    text: str,
    status: str = "accepted",
    *,
    spans: list[EvidenceSpan] | None = None,
    critical: bool = True,
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        claim=text,
        claim_type="factual_claim",
        critical=critical,
        support_status=status,
        confidence=0.9,
        evidence_spans=spans or [],
    )


def test_marker_pass_replaces_valid_markers_and_drops_unknown() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:r1:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = (
        "## Findings\n\n"
        "The system improved recall by 4.2 points. [[claim:job:claim:r1:01]]\n"
        "Unknown claim here. [[claim:job:claim:nope]]\n"
    )
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert result.markdown.startswith("## Findings")
    assert "4.2 points. [1]" in result.markdown
    assert "job:claim:nope" not in result.markdown
    assert result.dropped_markers == 1
    assert result.marker_cited_claim_ids == ("job:claim:r1:01",)
    assert result.coverage["cited_claim_count"] == 1
    assert result.coverage["dropped_markers"] == 1


def test_marker_pass_refuses_unsupported_claims() -> None:
    span = _span("span-1")
    contradicted = _claim(
        "job:claim:c:01",
        "The system improved recall by 4.2 points.",
        status="contradicted",
        spans=[span],
    )
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nThe system improved recall by 4.2 points. [[claim:job:claim:c:01]]\n"
    result = CitationInjector().inject(report, [contradicted], [span], sources)

    assert "[[claim:" not in result.markdown
    assert "4.2 points. [1]" not in result.markdown
    assert result.dropped_markers == 1
    assert result.cited_claim_ids == ()
    assert result.coverage["uncited_claim_count"] == 0


def test_verbatim_pass_cites_unmarked_claim_sentences() -> None:
    span = _span("span-1")
    claim = _claim(
        "job:claim:v:01",
        "The system improved recall by 4.2 points across all evaluated corpora.",
        spans=[span],
    )
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nBody text. The system improved recall by 4.2 points across all evaluated corpora.\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert "corpora. [1]" in result.markdown
    assert result.verbatim_cited_claim_ids == ("job:claim:v:01",)
    assert result.coverage["cited_claim_count"] == 1


def _prose(markdown: str) -> str:
    return markdown.split("## Claim Register", maxsplit=1)[0]


def test_verbatim_pass_skips_short_claims() -> None:
    span = _span("span-1", quote="Short.")
    claim = _claim("job:claim:s:01", "Recall improved.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nRecall improved.\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert "Recall improved. [1]" not in _prose(result.markdown)
    assert result.cited_claim_ids == ()
    assert result.coverage["uncited_claim_count"] == 1
    assert result.coverage["register_entries"] == 1


def test_references_section_lists_numbered_sources() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:r:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [
        _source("src-1", "doc-a", title="First Source"),
        _source("src-2", "doc-b", title="Second Source"),
    ]
    report = "## Findings\n\nThe system improved recall by 4.2 points. [[claim:job:claim:r:01]]\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert result.markdown.endswith("\n")
    assert "## References" in result.markdown
    assert "1. First Source — https://example.com/src-1 (document: doc-a)" in result.markdown
    assert "2. Second Source — https://example.com/src-2 (document: doc-b)" in result.markdown


def test_references_not_duplicated_when_already_present() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:r:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nText.\n\n## References\n\nExisting.\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert result.markdown.count("## References") == 1
    assert "Existing." in result.markdown


def test_injection_is_deterministic() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:d:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nThe system improved recall by 4.2 points. [[claim:job:claim:d:01]]\n"

    first = CitationInjector().inject(report, [claim], [span], sources).markdown
    second = CitationInjector().inject(report, [claim], [span], sources).markdown

    assert first == second


def test_injection_ignores_content_inside_code_fences() -> None:
    span = _span("span-1")
    claim = _claim(
        "job:claim:c:01",
        "The system improved recall by 4.2 points across all evaluated corpora.",
        spans=[span],
    )
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\n```\nThe system improved recall by 4.2 points across all evaluated corpora.\n```\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert "corpora. [1]" not in _prose(result.markdown)
    assert result.cited_claim_ids == ()
    assert "## Claim Register" in result.markdown


def test_injection_preserves_blank_line_paragraph_structure() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:b:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nThe system improved recall by 4.2 points. [[claim:job:claim:b:01]]\n\nBody paragraph two.\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert "\n\nThe system improved recall by 4.2 points. [1]\n\nBody paragraph two." in result.markdown


def test_claim_register_not_duplicated_when_present() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:r:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Findings\n\nThe system improved recall by 4.2 points.\n\n## Claim Register\n\nExisting entries.\n"
    result = CitationInjector().inject(report, [claim], [span], sources)

    assert result.markdown.count("## Claim Register") == 1
    assert "Existing entries." in result.markdown
    assert result.coverage["register_entries"] == 1


def test_bundle_compile_records_citation_coverage() -> None:
    span = _span("span-1")
    claim = _claim("job:claim:b:01", "The system improved recall by 4.2 points.", spans=[span])
    sources = [_source("src-1", "doc-a")]
    report = "## Executive Summary\n\nBody.\n\n## Findings\n\nThe system improved recall by 4.2 points. [[claim:job:claim:b:01]]\n"
    bundle = ReportBundleCompilerV2().compile(
        report_markdown=report,
        claims=[claim],
        evidence_packets=[],
        research_graph=__import__(
            "deep_research_agent.kernel.contracts", fromlist=["ResearchGraph"]
        ).ResearchGraph(),
        sources=sources,
        corpus_manifest=__import__(
            "deep_research_agent.kernel.contracts", fromlist=["CorpusManifest"]
        ).CorpusManifest(
            manifest_id="manifest-1",
            document_version_ids=["doc-a"],
            content_hashes={"doc-a": DOC_A},
            critical_claims_allowed={"doc-a": True},
        ),
        run_manifest={"job_id": "job-1"},
    )

    coverage = bundle.audit_summary["report_citation_coverage"]
    assert coverage["supported_claim_count"] == 1
    assert coverage["cited_claim_count"] == 1
    assert coverage["dropped_markers"] == 0
    assert "4.2 points. [1]" in bundle.report_markdown
    assert "## References" in bundle.report_markdown
    assert bundle.report_markdown.split("## References", maxsplit=1)[0].endswith("\n")
