from __future__ import annotations

from copy import deepcopy

import pytest


def _source(**overrides):
    from deep_research_agent.corpus.models import SourceDescriptor

    payload = {
        "source_id": "arxiv",
        "source_role": "primary_publication",
        "trust_tier": 1,
        "coverage": "AI/ML preprints",
        "official_base_uri": "https://arxiv.org",
        "access_method": "oai-pmh",
        "authentication_mode": "none",
        "rate_limit_policy": "polite",
        "incremental_cursor_type": "datestamp",
        "canonical_identifiers": ["arxiv"],
        "metadata_license": "CC0",
        "license": "CC-BY-4.0",
        "fulltext_license_strategy": "item-level",
        "storage_policy": "mirror_allowed",
        "redistribution_policy": "item-license",
        "freshness_sla": "daily",
        "fallback_sources": [],
        "health_probe": "oai",
        "parser_name": "grobid",
        "parser_version": "1",
        "supports_critical_claims": True,
    }
    payload.update(overrides)
    return SourceDescriptor(**payload)


def test_public_content_reuses_parsed_cache_but_private_document_stays_isolated():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    repository = InMemoryCorpusRepository()
    service = CorpusService(repository=repository)
    content = b"A paper about tool agents."
    public = service.ingest(
        source=_source(),
        content=content,
        title="Agents",
        source_native_id="arxiv:1",
        tenant_id=None,
    )
    public_again = service.ingest(
        source=_source(),
        content=content,
        title="Agents",
        source_native_id="arxiv:1",
        tenant_id=None,
    )
    private = service.ingest(
        source=_source(source_id="upload", source_role="user_corpus", storage_policy="user_supplied"),
        content=content,
        title="Private agents",
        source_native_id="upload:1",
        tenant_id="tenant-a",
    )

    assert public.document_version_id == public_again.document_version_id
    assert public.document_version_id != private.document_version_id
    assert service.search("agents", tenant_id="tenant-b") == [public]
    with pytest.raises(PermissionError):
        service.get_document(private.document_version_id, tenant_id="tenant-b")


def test_versions_are_preserved_and_license_policy_is_enforced():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    service = CorpusService(repository=InMemoryCorpusRepository())
    first = service.ingest(
        source=_source(),
        content=b"version one",
        title="Versioned",
        source_native_id="arxiv:2",
        version_label="v1",
    )
    second = service.ingest(
        source=_source(),
        content=b"version two",
        title="Versioned",
        source_native_id="arxiv:2",
        version_label="v2",
    )
    assert first.work_id == second.work_id
    assert first.document_version_id != second.document_version_id
    assert {first.version_label, second.version_label} == {"v1", "v2"}

    with pytest.raises(PermissionError):
        service.ingest(
            source=_source(storage_policy="link_only", license="unknown"),
            content=b"must not be stored",
            title="Restricted",
            source_native_id="restricted:1",
        )


def test_parser_falls_back_and_manifest_is_frozen():
    from deep_research_agent.corpus.models import ParsedDocument
    from deep_research_agent.corpus.parsers import DoclingParser, GrobidParser
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    class BrokenGrobid(GrobidParser):
        def parse(self, content, *, media_type="application/pdf"):
            raise RuntimeError("grobid unavailable")

    fallback = DoclingParser(
        parse_fn=lambda content, media_type="application/pdf": ParsedDocument(
            text=content.decode(), title="Fallback"
        )
    )
    service = CorpusService(
        repository=InMemoryCorpusRepository(), parsers=[BrokenGrobid(), fallback]
    )
    record = service.ingest(
        source=_source(),
        content=b"parsed text",
        title="Fallback",
        source_native_id="arxiv:3",
    )
    assert record.parser_name == "docling"
    manifest = service.freeze_manifest([record.document_version_id], tenant_id="default")
    assert manifest.document_version_ids == (record.document_version_id,)


def test_repository_returns_defensive_document_copies_and_freeze_is_idempotent():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    repository = InMemoryCorpusRepository()
    service = CorpusService(repository=repository)
    record = service.ingest(
        source=_source(),
        content=b"immutable document",
        title="Immutable",
        source_native_id="arxiv:immutable",
    )
    record.text = "tampered"
    record.metadata["tampered"] = True
    stored = service.get_document(record.document_version_id, tenant_id="tenant-a")
    assert stored.text == "immutable document"
    assert "tampered" not in stored.metadata

    first = service.freeze_manifest([stored.document_version_id], tenant_id="tenant-a")
    second = service.freeze_manifest([stored.document_version_id], tenant_id="tenant-a")
    assert first == second
    with pytest.raises((AttributeError, TypeError)):
        first.document_version_ids.append("tampered")
    with pytest.raises(TypeError):
        first.content_hashes[stored.document_version_id] = "tampered"
    copied = deepcopy(first)
    assert copied == first
    with pytest.raises(TypeError):
        copied.content_hashes[stored.document_version_id] = "tampered"


def test_derived_only_does_not_store_full_text_and_metadata_license_is_not_fulltext_license():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    source = _source(storage_policy="derived_only", license=None)
    with pytest.raises(PermissionError, match="license"):
        CorpusService(repository=InMemoryCorpusRepository()).ingest(
            source=source,
            content=b"licensed full text",
            title="No fulltext license",
            source_native_id="arxiv:no-license",
        )

    source = _source(storage_policy="derived_only", license="All rights reserved")
    record = CorpusService(repository=InMemoryCorpusRepository()).ingest(
        source=source,
        content=b"licensed full text",
        title="Derived",
        source_native_id="arxiv:derived",
    )
    assert record.text == ""
    assert record.metadata["storage_policy"] == "derived_only"
    assert record.metadata["content_length"] > 0

    with pytest.raises(PermissionError, match="redistributable"):
        CorpusService(repository=InMemoryCorpusRepository()).ingest(
            source=_source(storage_policy="mirror_allowed", license="unknown"),
            content=b"not redistributable",
            title="Unknown license",
            source_native_id="arxiv:unknown-license",
        )
    for lookalike in ("CC-BY-FAKE", "not-cc-by; all rights reserved", "miscellaneous proprietary"):
        with pytest.raises(PermissionError, match="redistributable"):
            CorpusService(repository=InMemoryCorpusRepository()).ingest(
                source=_source(storage_policy="mirror_allowed", license=lookalike),
                content=b"not redistributable",
                title="Lookalike license",
                source_native_id=f"arxiv:{lookalike}",
            )


def test_private_tenant_and_critical_claim_boundaries_fail_closed():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    service = CorpusService(repository=InMemoryCorpusRepository())
    with pytest.raises(ValueError, match="tenant_id"):
        service.ingest(
            source=_source(source_id="upload", source_role="user_corpus", storage_policy="user_supplied"),
            content=b"private",
            title="Private",
            source_native_id="upload:blank",
            tenant_id="",
        )
    with pytest.raises(PermissionError, match="critical"):
        service.ingest(
            source=_source(
                source_id="web",
                source_role="discovery",
                supports_critical_claims=False,
                storage_policy="derived_only",
                license="All rights reserved",
            ),
            content=b"discovery",
            title="Discovery",
            source_native_id="web:1",
            critical_claim=True,
        )
    discovery_source = _source(
        source_id="web",
        source_role="discovery",
        supports_critical_claims=False,
        storage_policy="derived_only",
        license="All rights reserved",
    )
    with pytest.raises(PermissionError, match="non-critical"):
        service.ingest(
            source=discovery_source,
            content=b"discovery",
            title="Discovery",
            source_native_id="web:2",
        )
    discovery = service.ingest(
        source=discovery_source,
        content=b"discovery",
        title="Discovery",
        source_native_id="web:2",
        critical_claim=False,
    )
    assert discovery.supports_critical_claims is False
    assert discovery.source_role == "discovery"
    with pytest.raises(PermissionError, match="critical"):
        service.require_critical_claim_support(discovery.document_version_id, tenant_id="tenant-a")


def test_private_grant_requires_owner_or_admin_actor():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    service = CorpusService(repository=InMemoryCorpusRepository())
    private = service.ingest(
        source=_source(source_id="upload", source_role="user_corpus", storage_policy="user_supplied"),
        content=b"private",
        title="Private",
        source_native_id="upload:1",
        tenant_id="owner",
    )
    with pytest.raises(PermissionError):
        service.grant_access(private.document_version_id, tenant_id="reader", actor_tenant_id="reader")
    with pytest.raises(PermissionError):
        service.grant_access(
            private.document_version_id,
            tenant_id="reader",
            actor_tenant_id="reader",
            actor_is_admin=True,
        )
    service.grant_access(private.document_version_id, tenant_id="reader", actor_tenant_id="owner")
    assert service.get_document(private.document_version_id, tenant_id="reader").title == "Private"


def test_private_work_identity_is_tenant_scoped():
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    service = CorpusService(repository=InMemoryCorpusRepository())
    first = service.ingest(
        source=_source(source_id="upload", source_role="user_corpus", storage_policy="user_supplied"),
        content=b"tenant one",
        title="Tenant One",
        source_native_id="upload:same",
        tenant_id="tenant-one",
    )
    second = service.ingest(
        source=_source(source_id="upload", source_role="user_corpus", storage_policy="user_supplied"),
        content=b"tenant two",
        title="Tenant Two",
        source_native_id="upload:same",
        tenant_id="tenant-two",
    )
    assert first.work_id != second.work_id
    assert service.get_document(second.document_version_id, tenant_id="tenant-two").title == "Tenant Two"


def test_discovery_documents_are_rejected_by_critical_evidence_audit():
    from deep_research_agent.auditor.semantic import EvidenceAuditor
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository
    from deep_research_agent.kernel.contracts import ArtifactRef, ClaimRecord, EvidenceSpan

    service = CorpusService(repository=InMemoryCorpusRepository())
    document = service.ingest(
        source=_source(
            source_id="web",
            source_role="discovery",
            supports_critical_claims=False,
            storage_policy="derived_only",
            license="All rights reserved",
        ),
        content=b"discovery",
        title="Discovery",
        source_native_id="web:audit",
        critical_claim=False,
    )
    manifest = service.freeze_manifest([document.document_version_id], tenant_id="tenant-a")
    span = EvidenceSpan(
        span_id="span-audit",
        document_version_id=document.document_version_id,
        section="body",
        quote="discovery",
        extraction_method="parser",
    )
    claim = ClaimRecord(
        claim_id="claim-audit",
        claim="Discovery source cannot support a critical claim",
        claim_type="fact",
        critical=True,
        support_status="accepted",
        confidence=0.9,
        evidence_spans=[span],
    )
    artifact = ArtifactRef(
        artifact_id="artifact-audit",
        uri="memory://discovery",
        media_type="text/plain",
        content_sha256=document.content_sha256,
        metadata={"document_version_id": document.document_version_id},
    )
    result = EvidenceAuditor().audit(
        [claim], manifest, evidence_spans=[span], source_artifacts=[artifact]
    )
    assert not result.accepted
    assert result.unsupported[0].support_status == "unsupported"
    assert result.degradations[claim.claim_id] == "critical_claim_source_not_allowed"


def test_fallback_parse_is_not_reused_as_primary_parser_cache():
    from deep_research_agent.corpus.models import ParsedDocument
    from deep_research_agent.corpus.parsers import DoclingParser, GrobidParser
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    class RecoveringGrobid(GrobidParser):
        available = False

        def parse(self, content, *, media_type="application/pdf"):
            if not self.available:
                raise RuntimeError("grobid is temporarily unavailable")
            return ParsedDocument(text="grobid")

    fallback_calls = 0

    def parse_fallback(content, **_):
        nonlocal fallback_calls
        fallback_calls += 1
        return ParsedDocument(text="docling")

    primary = RecoveringGrobid()
    service = CorpusService(
        repository=InMemoryCorpusRepository(),
        parsers=[
            primary,
            DoclingParser(parse_fn=parse_fallback),
        ],
    )
    first = service.ingest(
        source=_source(), content=b"same", title="Same", source_native_id="arxiv:same"
    )
    fallback_again = service.ingest(
        source=_source(), content=b"same", title="Same", source_native_id="arxiv:same"
    )
    assert fallback_again.document_version_id == first.document_version_id
    assert fallback_calls == 1
    primary.available = True
    second = service.ingest(
        source=_source(), content=b"same", title="Same", source_native_id="arxiv:same"
    )
    assert first.document_version_id != second.document_version_id
    assert second.parser_name == "grobid"
    assert second.text == "grobid"


@pytest.mark.parametrize(
    "license_name",
    ["CC-BY-FAKE", "not-cc-by; all rights reserved", "miscellaneous proprietary"],
)
def test_mirror_policy_rejects_lookalike_or_compound_licenses(license_name):
    from deep_research_agent.corpus.service import CorpusService
    from deep_research_agent.corpus.storage import InMemoryCorpusRepository

    with pytest.raises(PermissionError, match="redistributable"):
        CorpusService(repository=InMemoryCorpusRepository()).ingest(
            source=_source(license=license_name),
            content=b"restricted",
            title="Restricted",
            source_native_id=f"license:{license_name}",
        )


def test_connector_metadata_marks_arxiv_as_typed_and_open_web_discovery_only():
    from deep_research_agent.connectors.registry import build_connector_registry

    registry = build_connector_registry()
    assert registry.get("arxiv").supports_critical_claims is True
    assert registry.get("open_web").supports_critical_claims is False


def test_open_web_fetch_result_carries_non_advisory_critical_claim_marker():
    from deep_research_agent.connectors.legacy import LegacyConnectorAdapter
    from deep_research_agent.connectors.models import ConnectorCandidate

    adapter = LegacyConnectorAdapter(
        source_name="web",
        search_fn=lambda query, max_results=5: [],
        fetch_fn=lambda url: "discovery text",
        supports_critical_claims=False,
        source_role="discovery",
    )
    result = adapter.fetch(ConnectorCandidate(
        connector_name="open_web",
        source_type="web",
        title="Discovery",
        canonical_uri="https://example.com/paper",
        query="paper",
    ))
    assert result.supports_critical_claims is False
    assert result.source_role == "discovery"
