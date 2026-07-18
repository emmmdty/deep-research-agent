from __future__ import annotations

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
        "fulltext_license_strategy": "item-level",
        "storage_policy": "mirror_allowed",
        "redistribution_policy": "item-license",
        "freshness_sla": "daily",
        "fallback_sources": [],
        "health_probe": "oai",
        "parser_name": "grobid",
        "parser_version": "1",
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
    assert manifest.document_version_ids == [record.document_version_id]


def test_connector_metadata_marks_arxiv_as_typed_and_open_web_discovery_only():
    from deep_research_agent.connectors.registry import build_connector_registry

    registry = build_connector_registry()
    assert registry.get("arxiv").supports_critical_claims is True
    assert registry.get("open_web").supports_critical_claims is False
