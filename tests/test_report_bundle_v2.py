"""Evidence audit and deterministic V2 report-bundle tests."""

from __future__ import annotations

import json

import pytest

from deep_research_agent.auditor.semantic import EvidenceAuditor
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    CorpusManifest,
    EvidencePacket,
    EvidenceSpan,
    ResearchGraph,
    ResearchGraphEdge,
    ResearchGraphNode,
)
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2, load_report_bundle


DOC_HASH = "a" * 64


def _manifest() -> CorpusManifest:
    return CorpusManifest(
        manifest_id="manifest-1",
        document_version_ids=["doc-v1"],
        content_hashes={"doc-v1": DOC_HASH},
        critical_claims_allowed={"doc-v1": True},
    )


def _span(span_id: str = "span-1", *, document_version_id: str = "doc-v1") -> EvidenceSpan:
    return EvidenceSpan(
        span_id=span_id,
        document_version_id=document_version_id,
        page=7,
        section="4.2 Results",
        start_offset=120,
        end_offset=159,
        quote="The intervention improved recall by 4.2 points.",
        extraction_method="grobid_text_offsets",
    )


def _claim(
    claim_id: str,
    status: str,
    *,
    critical: bool = False,
    spans: list[EvidenceSpan] | None = None,
    text: str = "The intervention improved recall by 4.2 points.",
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        claim=text,
        claim_type="result",
        critical=critical,
        support_status=status,
        confidence=0.9,
        evidence_spans=spans or [],
    )


def _source() -> ArtifactRef:
    return ArtifactRef(
        artifact_id="source-1",
        uri="artifact://corpus/doc-v1",
        media_type="application/pdf",
        content_sha256=DOC_HASH,
        created_by_task_id="collect-1",
        metadata={"document_version_id": "doc-v1"},
    )


def _graph(span_id: str = "span-1") -> ResearchGraph:
    return ResearchGraph(
        nodes=[
            ResearchGraphNode(node_id="method", kind="method", label="Intervention"),
            ResearchGraphNode(node_id="metric", kind="metric", label="Recall"),
        ],
        edges=[
            ResearchGraphEdge(
                edge_id="edge-1",
                source_node_id="method",
                target_node_id="metric",
                relation="improves",
                evidence_span_ids=[span_id],
            )
        ],
    )


def test_bundle_preserves_exact_frozen_evidence_locators() -> None:
    span = _span()
    claim = _claim("claim-1", "accepted", critical=True, spans=[span])
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings\n",
        claims=[claim],
        evidence_packets=[EvidencePacket(packet_id="packet-1", task_id="collect-1", evidence_spans=[span], claims=[claim])],
        research_graph=_graph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1", "config_version_id": "config-v1"},
    )

    locator = bundle.accepted_claims[0].evidence_spans[0]
    assert locator.model_dump() == {
        "span_id": "span-1",
        "document_version_id": "doc-v1",
        "page": 7,
        "section": "4.2 Results",
        "start_offset": 120,
        "end_offset": 159,
        "quote": "The intervention improved recall by 4.2 points.",
        "extraction_method": "grobid_text_offsets",
    }
    assert bundle.evidence_matrix == {"claim-1": ["doc-v1"]}


def test_auditor_degrades_unfrozen_support_and_excludes_critical_claim_from_summary() -> None:
    unsupported = _claim(
        "claim-unfrozen",
        "accepted",
        critical=True,
        spans=[_span(document_version_id="doc-outside-manifest")],
        text="An unfrozen source proves the primary conclusion.",
    )

    audited = EvidenceAuditor().audit([unsupported], _manifest())

    assert audited.accepted == []
    assert audited.unsupported[0].support_status == "unsupported"
    assert audited.executive_summary_claims == []
    assert audited.degradations == {"claim-unfrozen": "evidence_outside_frozen_corpus"}


def test_bundle_keeps_contradictions_in_audit_not_supported_claim_buckets() -> None:
    span = _span()
    contradicted = _claim("claim-conflict", "contradicted", critical=True, spans=[span])

    bundle = ReportBundleCompilerV2().compile(
        report_markdown="## Executive Summary\n\nThe intervention improved recall by 4.2 points.\n\n## Detail\nBody.",
        claims=[contradicted],
        evidence_packets=[EvidencePacket(packet_id="packet-1", task_id="collect-1", evidence_spans=[span], claims=[contradicted])],
        research_graph=_graph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.qualified_claims == []
    assert bundle.audit_summary["contradicted_claim_ids"] == ["claim-conflict"]
    executive_summary = bundle.report_markdown.split("## Detail", maxsplit=1)[0]
    assert contradicted.claim not in executive_summary


def test_bundle_rebuilds_executive_summary_only_from_audited_claims() -> None:
    unsupported = _claim(
        "claim-blocked",
        "unsupported",
        critical=True,
        text="The primary outcome doubled.",
    )
    report = (
        "# Report\n\n## Executive Summary\n\n"
        "The main endpoint increased by one hundred percent.\n\n"
        "## Detail\n\nThis section may discuss limitations."
    )

    bundle = ReportBundleCompilerV2().compile(
        report_markdown=report,
        claims=[unsupported],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    executive_summary = bundle.report_markdown.split("## Detail", maxsplit=1)[0]
    assert "one hundred percent" not in executive_summary
    assert bundle.audit_summary["executive_summary_claim_ids"] == []


@pytest.mark.parametrize("heading", ["## Executive Summary:", "### EXECUTIVE SUMMARY"])
def test_bundle_canonicalizes_summary_heading_variants(heading: str) -> None:
    span = _span()
    claim = _claim("claim-1", "accepted", spans=[span])
    bundle = ReportBundleCompilerV2().compile(
        report_markdown=f"# Report\n\n{heading}\n\nold text\n\n## Detail\nBody.",
        claims=[claim],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert "## Executive Summary\n" in bundle.report_markdown
    assert "Executive Summary:" not in bundle.report_markdown
    assert "- The intervention improved recall by 4.2 points." in bundle.report_markdown


def test_bundle_strips_atx_closing_hash_summary_heading() -> None:
    span = _span()
    claim = _claim("claim-closing-hash", "accepted", spans=[span])
    bundle = ReportBundleCompilerV2().compile(
        report_markdown=(
            "# Report\n\n## Executive Summary ##\n\nUntrusted prose.\n\n"
            "## Detail\nBody."
        ),
        claims=[claim],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert "## Executive Summary ##" not in bundle.report_markdown
    assert "Untrusted prose." not in bundle.report_markdown
    assert "- The intervention improved recall by 4.2 points." in bundle.report_markdown


@pytest.mark.parametrize(
    "heading",
    [
        "##  Executive\tSummary  :  ##",
        "Executive   Summary\n=================",
    ],
)
def test_bundle_strips_whitespace_and_setext_summary_variants(heading: str) -> None:
    span = _span()
    claim = _claim("claim-heading-variant", "accepted", spans=[span])
    bundle = ReportBundleCompilerV2().compile(
        report_markdown=f"# Report\n\n{heading}\n\nUntrusted prose.\n\n## Detail\nBody.",
        claims=[claim],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert "Untrusted prose." not in bundle.report_markdown
    assert "- The intervention improved recall by 4.2 points." in bundle.report_markdown


def test_bundle_rejects_mixed_atx_and_setext_summary_duplicates() -> None:
    with pytest.raises(ValueError, match="ambiguous executive summary"):
        ReportBundleCompilerV2().compile(
            report_markdown=(
                "# Report\n\n## Executive Summary\nA\n\n"
                "Executive\tSummary\n------------------\nB"
            ),
            claims=[],
            evidence_packets=[],
            research_graph=ResearchGraph(),
            sources=[],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
        )


def test_bundle_rejects_ambiguous_duplicate_summary_headings() -> None:
    with pytest.raises(ValueError, match="ambiguous executive summary"):
        ReportBundleCompilerV2().compile(
            report_markdown="# Report\n\n## Executive Summary\nA\n\n### executive summary:\nB",
            claims=[],
            evidence_packets=[],
            research_graph=ResearchGraph(),
            sources=[],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
        )


def test_bundle_owns_summary_when_source_report_has_no_summary_heading() -> None:
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings\n\nBody.",
        claims=[],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.report_markdown.startswith("## Executive Summary\n")


@pytest.mark.parametrize("span_ids", [[], ["missing-span"]])
def test_bundle_rejects_graph_edges_without_exact_provenance(span_ids: list[str]) -> None:
    span = _span()
    accepted = _claim("claim-1", "accepted", spans=[span])
    graph = _graph()
    graph.edges[0].evidence_span_ids = span_ids

    with pytest.raises(ValueError, match="edge-1.*evidence"):
        ReportBundleCompilerV2().compile(
            report_markdown="# Findings",
            claims=[accepted],
            evidence_packets=[EvidencePacket(packet_id="packet-1", task_id="collect-1", evidence_spans=[span], claims=[accepted])],
            research_graph=graph,
            sources=[_source()],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
        )


def test_bundle_regeneration_is_deterministic_for_frozen_manifest() -> None:
    span_a = _span("span-a")
    span_b = _span("span-b")
    claim_a = _claim("claim-a", "accepted", spans=[span_a])
    claim_b = _claim("claim-b", "qualified", spans=[span_b])
    packet_a = EvidencePacket(packet_id="packet-a", task_id="collect-a", evidence_spans=[span_a], claims=[claim_a])
    packet_b = EvidencePacket(packet_id="packet-b", task_id="collect-b", evidence_spans=[span_b], claims=[claim_b])
    compiler = ReportBundleCompilerV2()
    kwargs = {
        "report_markdown": "# Frozen report",
        "research_graph": ResearchGraph(),
        "sources": [_source()],
        "corpus_manifest": _manifest(),
        "run_manifest": {"config_version_id": "config-v1", "job_id": "job-1"},
    }

    first = compiler.compile(claims=[claim_b, claim_a], evidence_packets=[packet_b, packet_a], **kwargs)
    second = compiler.compile(claims=[claim_a, claim_b], evidence_packets=[packet_a, packet_b], **kwargs)

    assert compiler.to_canonical_json(first) == compiler.to_canonical_json(second)
    assert json.loads(compiler.to_canonical_json(first))["schema_version"] == "2.0"


def test_bundle_uses_deduplicated_source_artifacts_from_evidence_packets() -> None:
    span = _span()
    accepted = _claim("claim-1", "accepted", spans=[span])
    source_b = _source().model_copy(update={"artifact_id": "source-b"})
    source_a = _source().model_copy(update={"artifact_id": "source-a"})
    packets = [
        EvidencePacket(
            packet_id="packet-b",
            task_id="collect-b",
            evidence_spans=[span],
            claims=[accepted],
            artifacts=[source_b],
        ),
        EvidencePacket(
            packet_id="packet-a",
            task_id="collect-a",
            evidence_spans=[span],
            claims=[accepted],
            artifacts=[source_a],
        ),
    ]

    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[accepted],
        evidence_packets=packets,
        research_graph=_graph(),
        sources=[],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert [source.artifact_id for source in bundle.sources] == ["source-a"]


def test_bundle_degrades_source_hash_mismatch() -> None:
    span = _span()
    accepted = _claim("claim-1", "accepted", critical=True, spans=[span])
    mismatched = _source().model_copy(update={"content_sha256": "b" * 64})

    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[accepted],
        evidence_packets=[EvidencePacket(packet_id="packet-1", task_id="collect-1", evidence_spans=[span], claims=[accepted])],
        research_graph=ResearchGraph(),
        sources=[mismatched],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.audit_summary["unsupported_claim_ids"] == ["claim-1"]
    assert bundle.audit_summary["degradations"]["claim-1"] == "source_hash_mismatch"


def test_bundle_degrades_claim_when_manifest_source_artifact_is_missing() -> None:
    span = _span()
    accepted = _claim("claim-missing-source", "accepted", critical=True, spans=[span])
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[accepted],
        evidence_packets=[],
        research_graph=ResearchGraph(),
        sources=[],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.audit_summary["degradations"]["claim-missing-source"] == "missing_source_artifact"


def test_bundle_consumes_unresolved_critic_decision_for_critical_claim() -> None:
    from deep_research_agent.orchestration.reducer import CriticDecision

    span = _span()
    claim = _claim("claim-unresolved", "accepted", critical=True, spans=[span])
    decision = CriticDecision(
        decision_id="critic-1",
        claim_ids=[claim.claim_id],
        decision="unresolved",
        rationale_evidence_ids=[span.span_id],
        rationale="The semantic disagreement remains unresolved.",
        unresolved=True,
    )
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[claim],
        evidence_packets=[],
        critic_decisions=[decision],
        research_graph=ResearchGraph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.audit_summary["unresolved_claim_ids"] == [claim.claim_id]


def test_bundle_rejects_critic_rationale_with_source_hash_mismatch() -> None:
    from deep_research_agent.orchestration.reducer import CriticDecision

    span = _span()
    claim = _claim("claim-critic-source", "accepted", critical=True, spans=[span])
    decision = CriticDecision(
        decision_id="critic-source-1",
        claim_ids=[claim.claim_id],
        decision="accepted",
        rationale_evidence_ids=[span.span_id],
        rationale="The source supports the claim.",
    )
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[claim],
        evidence_packets=[],
        critic_decisions=[decision],
        research_graph=ResearchGraph(),
        sources=[_source().model_copy(update={"content_sha256": "b" * 64})],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.audit_summary["unresolved_claim_ids"] == [claim.claim_id]


def test_bundle_fails_closed_when_critic_decisions_overlap_one_claim() -> None:
    from deep_research_agent.orchestration.reducer import CriticDecision

    span = _span()
    claim = _claim("claim-overlap", "accepted", critical=True, spans=[span])
    decisions = [
        CriticDecision(
            decision_id="critic-overlap-a",
            claim_ids=[claim.claim_id],
            decision="accepted",
            rationale_evidence_ids=[span.span_id],
            rationale="First resolution.",
        ),
        CriticDecision(
            decision_id="critic-overlap-b",
            claim_ids=[claim.claim_id],
            decision="contradicted",
            rationale_evidence_ids=[span.span_id],
            rationale="Conflicting resolution.",
        ),
    ]
    bundle = ReportBundleCompilerV2().compile(
        report_markdown="# Findings",
        claims=[claim],
        evidence_packets=[],
        critic_decisions=decisions,
        research_graph=ResearchGraph(),
        sources=[_source()],
        corpus_manifest=_manifest(),
        run_manifest={"job_id": "job-1"},
    )

    assert bundle.accepted_claims == []
    assert bundle.audit_summary["unresolved_claim_ids"] == [claim.claim_id]


def test_bundle_rejects_graph_provenance_outside_frozen_manifest() -> None:
    outside_span = _span(document_version_id="doc-outside-manifest")
    unsupported = _claim("claim-outside", "unsupported", spans=[outside_span])

    with pytest.raises(ValueError, match="edge-1.*frozen corpus"):
        ReportBundleCompilerV2().compile(
            report_markdown="# Findings",
            claims=[unsupported],
            evidence_packets=[
                EvidencePacket(
                    packet_id="packet-1",
                    task_id="collect-1",
                    evidence_spans=[outside_span],
                    claims=[unsupported],
                )
            ],
            research_graph=_graph(),
            sources=[_source()],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
        )


def test_legacy_bundle_loader_preserves_old_artifact_reads(tmp_path) -> None:
    legacy = {"job": {"job_id": "legacy-1", "runtime_path": "legacy-cli"}, "report": {"markdown": "# Old"}}
    path = tmp_path / "report_bundle.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")

    loaded = load_report_bundle(path)

    assert loaded == legacy
