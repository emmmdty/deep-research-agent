"""Deterministic citation-truthfulness verification tests (task 5, phase 2).

No network and no real LLM anywhere in this file: refetch and judge are always
fakes, and the frozen-corpus path must never touch a refetch callable.
"""

from __future__ import annotations

import json

from deep_research_agent.auditor.citation_verifier import (
    CitationVerificationRecord,
    CitationVerificationReport,
    CitationVerifier,
)
from deep_research_agent.kernel.contracts import (
    ArtifactRef,
    ClaimRecord,
    CorpusManifest,
    EvidencePacket,
    EvidenceSpan,
    ResearchGraph,
)
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2

DOC_HASH = "a" * 64

QUOTE = "The intervention improved recall by 4.2 points."


def _span(
    span_id: str = "span-1",
    *,
    quote: str = QUOTE,
    document_version_id: str = "doc-v1",
) -> EvidenceSpan:
    return EvidenceSpan(
        span_id=span_id,
        document_version_id=document_version_id,
        page=7,
        section="4.2 Results",
        start_offset=120,
        end_offset=159,
        quote=quote,
        extraction_method="agent_grounding",
    )


def _claim(
    claim_id: str,
    *,
    critical: bool = True,
    spans: list[EvidenceSpan] | None = None,
    text: str = "The intervention improved recall by 4.2 points.",
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        claim=text,
        claim_type="result",
        critical=critical,
        support_status="accepted",
        confidence=0.9,
        evidence_spans=spans or [],
    )


def _source(
    *,
    artifact_id: str = "source-1",
    uri: str = "https://example.com/doc-v1",
    document_version_id: str = "doc-v1",
    source_text: str | None = None,
) -> ArtifactRef:
    metadata: dict[str, object] = {"document_version_id": document_version_id}
    if source_text is not None:
        metadata["source_text"] = source_text
    return ArtifactRef(
        artifact_id=artifact_id,
        uri=uri,
        media_type="text/html",
        content_sha256=DOC_HASH,
        created_by_task_id="collect-1",
        metadata=metadata,
    )


def _manifest() -> CorpusManifest:
    return CorpusManifest(
        manifest_id="manifest-1",
        document_version_ids=["doc-v1"],
        content_hashes={"doc-v1": DOC_HASH},
        critical_claims_allowed={"doc-v1": True},
    )


def _ok_refetch(content: str):
    def refetch(url: str) -> dict[str, object]:
        return {
            "url": url,
            "final_url": url,
            "content": content,
            "fetch_status": "ok",
        }

    return refetch


def _never_called_refetch(url: str) -> dict[str, object]:  # pragma: no cover - sentinel
    raise AssertionError(f"refetch must not be called (got {url!r})")


class TestFrozenCorpusPath:
    def test_frozen_document_verifies_without_refetch(self) -> None:
        span = _span()
        claim = _claim("claim-1", spans=[span])
        source_text = f"Section 4.2 reports: {QUOTE}"
        source = _source(source_text=source_text)
        verifier = CitationVerifier(refetch=_never_called_refetch)

        report = verifier.verify(
            [claim],
            [source],
            document_contents={"doc-v1": source_text},
            job_id="job-1",
        )

        assert len(report.items) == 1
        item = report.items[0]
        assert item.claim_id == "claim-1"
        assert item.verdict == "verified"
        assert item.method == "deterministic"
        assert item.fetch_status == "frozen"
        assert item.quote_contained is True
        assert item.source_url == "https://example.com/doc-v1"
        assert item.document_version_id == "doc-v1"
        assert 0.0 < item.support_score <= 1.0
        assert report.summary == {
            "total": 1,
            "verified": 1,
            "unsupported": 0,
            "unverifiable": 0,
            "fetch_failed": 0,
        }

    def test_quote_present_in_frozen_text_beats_judge(self) -> None:
        span = _span()
        claim = _claim("claim-judge-idle", spans=[span])
        source_text = f"Evidence: {QUOTE}"

        def judge(claim_text: str, source_text_: str) -> str:  # pragma: no cover - sentinel
            raise AssertionError("judge must not be called when the quote is contained")

        verifier = CitationVerifier(refetch=_never_called_refetch, judge=judge)
        report = verifier.verify(
            [claim],
            [_source(source_text=source_text)],
            document_contents={"doc-v1": source_text},
            job_id="job-1",
        )

        assert report.items[0].method == "deterministic"
        assert report.items[0].verdict == "verified"


class TestCriticalityGating:
    def test_non_critical_claims_are_skipped_entirely(self) -> None:
        span = _span()
        claim = _claim("claim-minor", critical=False, spans=[span])
        verifier = CitationVerifier(refetch=_never_called_refetch)

        report = verifier.verify(
            [claim],
            [_source(source_text=QUOTE)],
            document_contents={"doc-v1": QUOTE},
            job_id="job-1",
        )

        assert report.items == []
        assert report.summary == {
            "total": 0,
            "verified": 0,
            "unsupported": 0,
            "unverifiable": 0,
            "fetch_failed": 0,
        }


class TestRefetchPaths:
    def test_fake_refetch_with_quote_verifies(self) -> None:
        span = _span()
        claim = _claim("claim-refetch", spans=[span])
        fetched_content = f"Live page: {QUOTE}"
        refetch = _ok_refetch(fetched_content)
        called_with: list[str] = []

        def recording_refetch(url: str) -> dict[str, object]:
            called_with.append(url)
            return refetch(url)

        verifier = CitationVerifier(refetch=recording_refetch)
        report = verifier.verify(
            [claim],
            [_source()],
            document_contents={},
            job_id="job-1",
        )

        item = report.items[0]
        assert item.verdict == "verified"
        assert item.method == "deterministic"
        assert item.fetch_status == "ok"
        assert item.quote_contained is True
        assert called_with == ["https://example.com/doc-v1"]

    def test_failed_refetch_yields_fetch_failed_verdict(self) -> None:
        span = _span()
        claim = _claim("claim-fetch-failed", spans=[span])

        def failed_refetch(url: str) -> dict[str, object]:
            return {
                "url": url,
                "final_url": url,
                "content": "",
                "fetch_status": "failed",
            }

        verifier = CitationVerifier(refetch=failed_refetch)
        report = verifier.verify(
            [claim],
            [_source()],
            document_contents={},
            job_id="job-1",
        )

        item = report.items[0]
        assert item.verdict == "fetch_failed"
        assert item.method == "fetch_failed"
        assert item.fetch_status == "failed"
        assert item.quote_contained is False
        assert item.support_score == 0.0

    def test_default_refetch_never_raises_on_fetch_error(self, monkeypatch) -> None:
        import deep_research_agent.connectors.tools.page_fetch as page_fetch_module

        span = _span()
        claim = _claim("claim-default-refetch", spans=[span])

        def boom(url: str) -> dict[str, object]:
            raise ValueError(f"cannot reach {url}")

        monkeypatch.setattr(page_fetch_module, "fetch_page", boom)
        verifier = CitationVerifier()
        report = verifier.verify(
            [claim],
            [_source()],
            document_contents={},
            job_id="job-1",
        )

        item = report.items[0]
        assert item.verdict == "fetch_failed"
        assert item.method == "fetch_failed"
        assert item.fetch_status == "failed"
        assert report.summary["fetch_failed"] == 1


class TestJudgePaths:
    def _report_with_judge(self, judge, *, quote_in_source: bool = False):
        span = _span()
        claim = _claim("claim-judged", spans=[span])
        source_text = "Related prose without the exact quote." if not quote_in_source else QUOTE
        verifier = CitationVerifier(refetch=_never_called_refetch, judge=judge)
        return verifier.verify(
            [claim],
            [_source(source_text=source_text)],
            document_contents={"doc-v1": source_text},
            job_id="job-1",
        )

    def test_judge_verified_never_upgrades_absent_quote(self) -> None:
        """quote 缺失时 LLM judge 只能 downgrade：判 verified 也不得放行。"""
        report = self._report_with_judge(lambda claim_text, source_text: "verified")
        item = report.items[0]
        assert item.verdict == "unverifiable"
        assert item.method == "deterministic"
        assert item.quote_contained is False
        assert "only downgrade" in item.rationale

    def test_judge_none_yields_unverifiable(self) -> None:
        report = self._report_with_judge(lambda claim_text, source_text: None)
        item = report.items[0]
        assert item.verdict == "unverifiable"
        assert item.method == "deterministic"

    def test_judge_contradicted_maps_to_unsupported(self) -> None:
        report = self._report_with_judge(lambda claim_text, source_text: "contradicted")
        item = report.items[0]
        assert item.verdict == "unsupported"
        assert item.method == "llm_judge"

    def test_judge_unsupported_maps_to_unsupported(self) -> None:
        report = self._report_with_judge(lambda claim_text, source_text: "unsupported")
        item = report.items[0]
        assert item.verdict == "unsupported"
        assert item.method == "llm_judge"

    def test_no_judge_and_quote_absent_yields_unverifiable(self) -> None:
        span = _span()
        claim = _claim("claim-no-judge", spans=[span])
        verifier = CitationVerifier(refetch=_never_called_refetch)
        report = verifier.verify(
            [claim],
            [_source(source_text="Unrelated body text.")],
            document_contents={"doc-v1": "Unrelated body text."},
            job_id="job-1",
        )

        item = report.items[0]
        assert item.verdict == "unverifiable"
        assert item.method == "deterministic"
        assert item.quote_contained is False
        assert report.summary["unverifiable"] == 1


class TestMaxVerifications:
    def test_cap_limits_verified_items_sorted_by_claim_id(self) -> None:
        claims = [
            _claim(f"claim-{suffix}", spans=[_span(f"span-{suffix}")]) for suffix in ("c", "a", "b")
        ]
        refetch = _ok_refetch(f"Live page: {QUOTE}")
        verifier = CitationVerifier(refetch=refetch, max_verifications=2)
        report = verifier.verify(claims, [_source()], document_contents={}, job_id="job-1")

        assert [item.claim_id for item in report.items] == ["claim-a", "claim-b"]
        assert report.summary == {
            "total": 2,
            "verified": 2,
            "unsupported": 0,
            "unverifiable": 0,
            "fetch_failed": 0,
            "critical_claims_skipped": 1,
        }


class TestUnknownDocument:
    def test_unknown_document_never_raises_and_skips_refetch(self) -> None:
        span = _span(document_version_id="doc-unknown")
        claim = _claim("claim-unknown-doc", spans=[span])
        verifier = CitationVerifier(refetch=_never_called_refetch)

        report = verifier.verify([claim], [], document_contents={}, job_id="job-1")

        item = report.items[0]
        assert item.verdict == "unverifiable"
        assert item.method == "deterministic"
        assert item.fetch_status == "skipped"
        assert item.source_url == ""
        assert item.document_version_id == "doc-unknown"
        assert item.quote_contained is False


class TestReportModel:
    def test_record_model_rejects_unknown_fields(self) -> None:
        CitationVerificationRecord(
            verification_id="job-1:verify:claim-1",
            claim_id="claim-1",
            claim_text="text",
            source_url="https://example.com",
            document_version_id="doc-v1",
            method="deterministic",
            verdict="verified",
            quote_contained=True,
            support_score=0.5,
            rationale="quote contained",
            fetch_status="frozen",
        )
        try:
            CitationVerificationRecord(
                verification_id="v",
                claim_id="c",
                claim_text="t",
                source_url="u",
                document_version_id="d",
                method="deterministic",
                verdict="verified",
                quote_contained=True,
                support_score=0.5,
                rationale="r",
                fetch_status="frozen",
                surprise=True,
            )
        except Exception as exc:
            assert "surprise" in str(exc)
        else:  # pragma: no cover - must reject
            raise AssertionError("extra field must be rejected")

    def test_report_model_defaults(self) -> None:
        report = CitationVerificationReport(job_id="job-1")
        assert report.items == []
        assert report.created_at
        assert report.summary["total"] == 0


class TestCompileIntegration:
    def test_bundle_carries_citation_verification_in_audit_summary(self) -> None:
        span = _span()
        claim = _claim("claim-bundle", spans=[span])
        source_text = f"Full text with {QUOTE}"
        source = _source(source_text=source_text)
        verifier = CitationVerifier(refetch=_never_called_refetch)
        verification = verifier.verify(
            [claim],
            [source],
            document_contents={"doc-v1": source_text},
            job_id="job-1",
        )
        payload = verification.model_dump(mode="json")

        bundle = ReportBundleCompilerV2().compile(
            report_markdown="# Findings\n",
            claims=[claim],
            evidence_packets=[
                EvidencePacket(
                    packet_id="packet-1",
                    task_id="collect-1",
                    evidence_spans=[span],
                    claims=[claim],
                )
            ],
            research_graph=ResearchGraph(),
            sources=[source],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
            citation_verification=payload,
        )

        assert bundle.audit_summary["citation_verification"] == payload
        assert bundle.audit_summary["citation_verification"]["summary"]["verified"] == 1
        canonical = ReportBundleCompilerV2.to_canonical_json(bundle)
        assert json.loads(canonical)["schema_version"] == "2.0"
        assert (
            json.loads(canonical)["audit_summary"]["citation_verification"]["items"][0]["verdict"]
            == "verified"
        )

    def test_bundle_defaults_citation_verification_to_empty_mapping(self) -> None:
        span = _span()
        claim = _claim("claim-bundle-default", spans=[span])
        bundle = ReportBundleCompilerV2().compile(
            report_markdown="# Findings\n",
            claims=[claim],
            evidence_packets=[
                EvidencePacket(
                    packet_id="packet-1",
                    task_id="collect-1",
                    evidence_spans=[span],
                    claims=[claim],
                )
            ],
            research_graph=ResearchGraph(),
            sources=[_source(source_text=QUOTE)],
            corpus_manifest=_manifest(),
            run_manifest={"job_id": "job-1"},
        )

        assert bundle.audit_summary["citation_verification"] == {}


class TestToDisk:
    def test_to_disk_writes_valid_utf8_json(self, tmp_path) -> None:
        span = _span()
        claim = _claim("claim-disk", text="干预措施将召回率提升了 4.2 个百分点", spans=[span])
        source_text = f"实验记录: {claim.claim}"
        verifier = CitationVerifier(refetch=_never_called_refetch)
        report = verifier.verify(
            [claim],
            [_source(source_text=source_text)],
            document_contents={"doc-v1": source_text},
            job_id="job-1",
        )

        path = verifier.to_disk(report, tmp_path)

        assert path.name == "citation_verification.json"
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        assert payload == report.model_dump(mode="json")
        assert "干预措施" in raw
        assert "\\u5e72\\u9884" not in raw

    def test_to_disk_creates_parent_directories(self, tmp_path) -> None:
        verifier = CitationVerifier(refetch=_never_called_refetch)
        report = CitationVerificationReport(job_id="job-1")
        target = tmp_path / "nested" / "output"

        path = verifier.to_disk(report, target)

        assert path.parent == target
        assert path.exists()


class TestMultiSpanClaims:
    """合并后的 claim 带多个文档 span：每个 quote 必须在其自身文档中被核验。"""

    def test_multi_span_claim_requires_quote_in_each_own_document(self) -> None:
        second_quote = "A second finding with its own grounding text."
        claim = _claim(
            "claim-multi-span",
            spans=[
                _span("span-a", quote=QUOTE, document_version_id="doc-a"),
                _span("span-b", quote=second_quote, document_version_id="doc-b"),
            ],
        )
        sources = [
            _source(source_text=f"Doc A: {QUOTE}", document_version_id="doc-a", uri="https://a/"),
            _source(
                source_text=f"Doc B: {second_quote}", document_version_id="doc-b", uri="https://b/"
            ),
        ]
        verifier = CitationVerifier()

        report = verifier.verify(
            [claim],
            sources,
            document_contents={
                "doc-a": f"Doc A: {QUOTE}",
                "doc-b": f"Doc B: {second_quote}",
            },
            job_id="job-1",
        )
        item = report.items[0]

        assert item.verdict == "verified"
        assert item.quote_contained is True

    def test_multi_span_claim_fails_when_one_quote_missing_in_its_document(self) -> None:
        """span-b 的 quote 不在 doc-b 里，即使 doc-a 命中也不得判 verified。"""
        second_quote = "A second finding with its own grounding text."
        claim = _claim(
            "claim-multi-span-missing",
            spans=[
                _span("span-a", quote=QUOTE, document_version_id="doc-a"),
                _span("span-b", quote=second_quote, document_version_id="doc-b"),
            ],
        )
        sources = [
            _source(source_text=f"Doc A: {QUOTE}", document_version_id="doc-a", uri="https://a/"),
            # doc-b 的正文里没有 span-b 的 quote（被合并时混入了别的文档引用）
            _source(
                source_text="Doc B unrelated text.", document_version_id="doc-b", uri="https://b/"
            ),
        ]
        verifier = CitationVerifier()

        report = verifier.verify(
            [claim],
            sources,
            document_contents={"doc-a": f"Doc A: {QUOTE}", "doc-b": "Doc B unrelated text."},
            job_id="job-1",
        )
        item = report.items[0]

        assert item.verdict == "unverifiable"
        assert item.quote_contained is False

    def test_multi_span_refetch_per_document_is_called_once(self) -> None:
        second_quote = "A second finding with its own grounding text."
        claim = _claim(
            "claim-multi-span-refetch",
            spans=[
                _span("span-a", quote=QUOTE, document_version_id="doc-a"),
                _span("span-b", quote=second_quote, document_version_id="doc-b"),
            ],
        )
        called: list[str] = []

        def refetch(url: str) -> dict:
            called.append(url)
            if url == "https://a/":
                return {
                    "url": url,
                    "final_url": url,
                    "content": f"Doc A: {QUOTE}",
                    "fetch_status": "ok",
                }
            return {
                "url": url,
                "final_url": url,
                "content": f"Doc B: {second_quote}",
                "fetch_status": "ok",
            }

        sources = [
            _source(source_text="ignored", document_version_id="doc-a", uri="https://a/"),
            _source(source_text="ignored", document_version_id="doc-b", uri="https://b/"),
        ]
        verifier = CitationVerifier(refetch=refetch)

        report = verifier.verify([claim], sources, document_contents={}, job_id="job-1")

        assert report.items[0].verdict == "verified"
        assert sorted(called) == ["https://a/", "https://b/"]
        assert len(called) == 2
