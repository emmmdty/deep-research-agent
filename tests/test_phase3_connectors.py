"""Phase 03 connector substrate、snapshot 与 source policy 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from legacy.workflows.states import RunMetrics, SourceRecord


PHASE3_SCHEMA_NAMES = [
    "artifact-manifest",
    "connector-health-record",
    "source-policy-profile",
    "source-policy-overrides",
]


@pytest.mark.parametrize("schema_name", PHASE3_SCHEMA_NAMES)
def test_phase3_schema_files_exist_and_are_loadable(schema_name: str):
    """Phase 03 新增 schema 应存在且可加载。"""
    from artifacts.schemas import load_schema

    schema = load_schema(schema_name)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"


def test_source_policy_profile_schema_validation():
    """source policy profile fixture 应通过 schema 校验。"""
    from artifacts.schemas import validate_instance

    payload = {
        "profile_name": "trusted-web",
        "description": "只允许受信域名的公开网页研究。",
        "connectors": ["open_web", "github"],
        "connector_order": ["open_web", "github"],
        "allow_domains": ["docs.langchain.com", "github.com"],
        "deny_domains": ["reddit.com"],
        "auth_scopes": ["public"],
        "budget": {
            "max_candidates_per_connector": 4,
            "max_fetches_per_task": 3,
            "max_total_fetches": 8,
        },
    }

    validate_instance("source-policy-profile", payload)


def test_source_policy_overrides_schema_rejects_negative_budget():
    """policy overrides 不允许负预算。"""
    from artifacts.schemas import validate_instance

    payload = {
        "allow_domains": ["docs.langchain.com"],
        "budget": {"max_total_fetches": -1},
    }

    with pytest.raises(ValidationError):
        validate_instance("source-policy-overrides", payload)


def test_snapshot_store_persists_manifest_and_text(tmp_path: Path):
    """snapshot store 应持久化文本与 manifest。"""
    from connectors.snapshot_store import SnapshotInput, SnapshotStore

    store = SnapshotStore(root=tmp_path / "snapshots")
    snapshot = store.persist(
        SnapshotInput(
            connector_name="open_web",
            source_type="web",
            canonical_uri="https://Example.com/docs?page=1&utm_source=test#frag",
            title="LangGraph Docs",
            text="LangGraph is a framework for building long-running agents.",
            mime_type="text/html",
            auth_scope="public",
            query="LangGraph docs",
            metadata={"published_at": "2026-04-09", "domain": "example.com"},
        )
    )

    manifest_path = tmp_path / "snapshots" / f"{snapshot.snapshot_id}.json"
    text_path = tmp_path / "snapshots" / f"{snapshot.snapshot_id}.txt"

    assert manifest_path.exists()
    assert text_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["canonical_uri"] == "https://example.com/docs?page=1"
    assert manifest["auth_scope"] == "public"
    assert manifest["freshness_metadata"]["query"] == "LangGraph docs"


def test_legacy_connectors_search_and_fetch_return_snapshot_ready_payloads():
    """legacy adapter 应把旧工具结果归一成统一 contract。"""
    from connectors.legacy import LegacyConnectorAdapter

    adapter = LegacyConnectorAdapter(
        source_name="web",
        search_fn=lambda query, max_results=5: [
            {
                "title": "LangGraph Docs",
                "url": "https://docs.langchain.com/langgraph",
                "snippet": "LangGraph helps build long-running, stateful agents.",
                "published_at": "2026-04-09",
            }
        ],
        fetch_fn=lambda url: {
            "text": "LangGraph helps build long-running, stateful agents.",
            "mime_type": "text/html",
            "status_code": 200,
        },
    )

    candidates = adapter.search("LangGraph", max_results=3)
    fetched = adapter.fetch(candidates[0])

    assert candidates[0].canonical_uri == "https://docs.langchain.com/langgraph"
    assert fetched.text.startswith("LangGraph helps")
    assert fetched.auth_scope == "public"
    assert fetched.freshness_metadata["published_at"] == "2026-04-09"


def test_source_policy_enforces_allow_deny_and_budget():
    """source policy 应在域名与 budget 两侧生效。"""
    from connectors.models import ConnectorCandidate
    from policies.models import ConnectorBudget, SourcePolicyOverrides
    from policies.source_policy import SourcePolicy

    policy = SourcePolicy(
        profile_name="trusted-web",
        connectors=["open_web"],
        connector_order=["open_web"],
        allow_domains=["docs.langchain.com", "github.com"],
        deny_domains=["reddit.com"],
        auth_scopes=["public"],
        budget=ConnectorBudget(max_candidates_per_connector=2, max_fetches_per_task=1, max_total_fetches=2),
    )
    overrides = SourcePolicyOverrides(
        allow_domains=["reference.langchain.com"],
        deny_domains=["github.com"],
        budget=ConnectorBudget(max_candidates_per_connector=1, max_fetches_per_task=1, max_total_fetches=1),
    )
    effective = policy.with_overrides(overrides)

    kept = effective.filter_candidates(
        [
            ConnectorCandidate(
                connector_name="open_web",
                source_type="web",
                title="Reference",
                canonical_uri="https://reference.langchain.com/python/langgraph/",
                query="LangGraph reference",
                snippet="reference docs",
            ),
            ConnectorCandidate(
                connector_name="open_web",
                source_type="web",
                title="GitHub",
                canonical_uri="https://github.com/langchain-ai/langgraph",
                query="LangGraph repo",
                snippet="repo",
            ),
        ]
    )

    assert len(kept.allowed) == 1
    assert kept.allowed[0].domain == "reference.langchain.com"
    assert kept.blocked[0].reason == "domain_denied"
    assert effective.budget.max_total_fetches == 1


def test_source_policy_blocks_unsafe_fetch_uris():
    """fetch policy 应拒绝非 http(s)、localhost 与私网地址。"""
    from policies.source_policy import SourcePolicy

    policy = SourcePolicy(profile_name="open-web", connectors=["open_web"], connector_order=["open_web"])

    assert policy.validate_fetch_uri("file:///etc/passwd").allowed is False
    assert policy.validate_fetch_uri("file:///etc/passwd").reason == "unsupported_scheme"
    assert policy.validate_fetch_uri("http://localhost:8000").allowed is False
    assert policy.validate_fetch_uri("http://localhost:8000").reason == "private_or_local_host"
    assert policy.validate_fetch_uri("http://127.0.0.1:8000").allowed is False
    assert policy.validate_fetch_uri("http://10.0.0.12/internal").allowed is False
    assert policy.validate_fetch_uri("https://docs.langchain.com/langgraph").allowed is True


def test_web_fetch_rejects_unsafe_url_before_scraper():
    """web fetch adapter 自身应拒绝不安全 URL，避免绕过 researcher policy。"""
    from connectors import registry

    with pytest.raises(ValueError, match="private_or_local_host"):
        registry._web_fetch("http://127.0.0.1:8000")


def test_researcher_does_not_fetch_policy_blocked_private_url(tmp_path: Path, monkeypatch):
    """collecting 遇到 fetch policy 拦截的 URL 时，不应调用 connector fetch。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "open-web",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    class StaticLLM:
        def invoke(self, messages):
            return type("Response", (), {"content": "No usable public sources."})()

    monkeypatch.setattr(researcher, "get_llm", lambda: StaticLLM())

    def forbidden_fetch(url):
        raise AssertionError(f"fetch should not be called for {url}")

    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "Internal Admin",
                            "url": "http://127.0.0.1:8000/admin",
                            "snippet": "private admin page",
                        }
                    ],
                    fetch_fn=forbidden_fetch,
                )
            }
        ),
    )

    result = researcher.researcher_node(
        {
            "research_topic": "internal admin",
            "research_profile": "default",
            "source_profile": "open-web",
            "tasks": [
                TaskItem(
                    id=1,
                    title="安全",
                    intent="验证 fetch policy",
                    query="internal admin",
                    preferred_sources=["web"],
                )
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "source_snapshots": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["sources_gathered"] == []
    assert result["source_snapshots"] == []
    assert result["connector_health"]["open_web"]["policy_blocked"] == 1
    assert result["connector_health"]["open_web"]["last_error"] == "private_or_local_host"


def test_phase3_source_record_and_verifier_preserve_snapshot_ref(tmp_path: Path, monkeypatch):
    """verifier 生成的 evidence unit 应继承 snapshot_ref。"""
    from legacy.agents import verifier

    settings = type("Settings", (), {"workspace_dir": str(tmp_path / "workspace")})()
    monkeypatch.setattr(verifier, "get_settings", lambda: settings)

    result = verifier.verifier_node(
        {
            "research_topic": "LangGraph 是什么",
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_id="source-1",
                    source_type="web",
                    query="LangGraph",
                    title="LangGraph Docs",
                    canonical_uri="https://docs.langchain.com/langgraph",
                    url="https://docs.langchain.com/langgraph",
                    snippet="LangGraph helps build long-running agents.",
                    snapshot_ref="snapshot-1",
                    fetched_at="2026-04-09T00:00:00+00:00",
                    mime_type="text/html",
                    auth_scope="public",
                    freshness_metadata={"published_at": "2026-04-09"},
                    trust_tier=4,
                    selected=True,
                )
            ],
            "run_metrics": RunMetrics(),
            "evidence_notes": [],
        }
    )

    assert result["evidence_units"][0].snapshot_ref == "snapshot-1"


def test_phase3_bundle_prefers_real_snapshots_over_synthetic():
    """bundle 构建器在 state 已有真实 snapshot 时应直接使用。"""
    from artifacts.bundle import build_report_bundle

    result = {
        "research_topic": "LangGraph",
        "research_profile": "default",
        "status": "completed",
        "final_report": "# 报告\n\nLangGraph 是一个用于有状态 agent 的框架。[1]",
        "sources_gathered": [
            {
                "citation_id": 1,
                "source_id": "source-1",
                "source_type": "web",
                "query": "LangGraph",
                "title": "LangGraph Docs",
                "canonical_uri": "https://docs.langchain.com/langgraph",
                "url": "https://docs.langchain.com/langgraph",
                "snippet": "LangGraph helps build long-running agents.",
                "snapshot_ref": "snapshot-real-1",
                "fetched_at": "2026-04-09T00:00:00+00:00",
                "mime_type": "text/html",
                "auth_scope": "public",
                "freshness_metadata": {"published_at": "2026-04-09"},
                "selected": True,
            }
        ],
        "source_snapshots": [
            {
                "snapshot_id": "snapshot-real-1",
                "canonical_uri": "https://docs.langchain.com/langgraph",
                "fetched_at": "2026-04-09T00:00:00+00:00",
                "content_hash": "abc123456789",
                "mime_type": "text/html",
                "auth_scope": "public",
                "freshness_metadata": {"published_at": "2026-04-09"},
            }
        ],
        "evidence_notes": [],
        "run_metrics": {"llm_calls": 1, "search_calls": 1},
    }

    bundle = build_report_bundle(
        result,
        job_id="job-phase3-001",
        max_loops=2,
        research_profile="default",
        source_profile="trusted-web",
        report_bundle_ref="bundle/report_bundle.json",
        trace_events=[],
        runtime_path="orchestrator-v1",
    )

    assert bundle["snapshots"][0]["snapshot_id"] == "snapshot-real-1"
    assert bundle["sources"][0]["snapshot_ref"] == "snapshot-real-1"


def test_researcher_collecting_uses_connectors_and_emits_snapshots(tmp_path: Path, monkeypatch):
    """collecting 应把 fetched source 转成带 snapshot_ref 的 SourceRecord。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "trusted-web",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "LangGraph Docs",
                            "url": "https://docs.langchain.com/langgraph",
                            "snippet": "LangGraph helps build stateful agents.",
                        }
                    ],
                    fetch_fn=lambda url: {
                        "text": "LangGraph helps build stateful agents.",
                        "mime_type": "text/html",
                    },
                )
            }
        ),
    )

    result = researcher.researcher_node(
        {
            "research_topic": "LangGraph 是什么",
            "research_profile": "benchmark",
            "source_profile": "trusted-web",
            "policy_overrides": {"allow_domains": ["docs.langchain.com"]},
            "tasks": [
                TaskItem(
                    id=1,
                    title="定义",
                    intent="解释概念",
                    query="LangGraph 是什么",
                    task_type="research",
                    expected_aspects=["LangGraph 是什么"],
                    preferred_sources=["web"],
                )
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "source_snapshots": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["sources_gathered"]
    assert result["sources_gathered"][0].snapshot_ref
    assert result["source_snapshots"]
    assert result["source_snapshots"][0]["snapshot_id"] == result["sources_gathered"][0].snapshot_ref


def test_researcher_expands_official_page_to_linked_pdf_snapshot(tmp_path: Path, monkeypatch):
    """collecting 应跟随官方页面中的技术报告 PDF，并把 PDF 作为可审计 snapshot。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import RunMetrics, TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "industry_broad",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "_fetch_remote_pdf_text",
        lambda url, workspace_dir: (
            "DeepSeek-V4-Pro has 1.6T total parameters and 49B active parameters. "
            "DeepSeek Sparse Attention supports 1M context.",
            {"download_url": url, "page_count": 1},
        ),
        raising=False,
    )
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "DeepSeek V4 Preview Release",
                            "url": "https://api-docs.deepseek.com/news/news260424",
                            "snippet": "DeepSeek-V4 Preview is officially live.",
                        }
                    ],
                    fetch_fn=lambda url: {
                        "text": (
                            "<html><body><h1>DeepSeek V4 Preview Release</h1>"
                            "<a href=\"https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/"
                            "blob/main/DeepSeek_V4.pdf\">Tech Report</a></body></html>"
                        ),
                        "mime_type": "text/html",
                    },
                )
            }
        ),
    )

    result = researcher.researcher_node(
        {
            "research_topic": "DeepSeek-V4 architecture",
            "research_profile": "benchmark",
            "source_profile": "industry_broad",
            "policy_overrides": {
                "allow_domains": ["api-docs.deepseek.com", "huggingface.co"],
                "budget": {"max_candidates_per_connector": 4, "max_fetches_per_task": 4, "max_total_fetches": 6},
            },
            "tasks": [
                TaskItem(
                    id=1,
                    title="DeepSeek-V4 MoE 架构",
                    intent="确认官方技术报告中的架构参数",
                    query="DeepSeek V4 Preview Release official technical report",
                    task_type="research",
                    preferred_sources=["web"],
                    must_include_terms=["DeepSeek", "V4", "1.6T", "DSA"],
                )
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "source_snapshots": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    pdf_sources = [source for source in result["sources_gathered"] if source.mime_type == "application/pdf"]
    assert len(pdf_sources) == 1
    assert pdf_sources[0].canonical_uri == "https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf"
    assert "1.6T total parameters" in pdf_sources[0].snippet
    assert pdf_sources[0].metadata["parent_source_id"] == "source-1"
    assert pdf_sources[0].metadata["discovery_reason"] == "technical_report_link"
    assert any(snapshot["mime_type"] == "application/pdf" for snapshot in result["source_snapshots"])
    assert result["run_metrics"].remote_pdfs_ingested == 1


def test_researcher_blocks_linked_pdf_outside_source_policy(tmp_path: Path, monkeypatch):
    """页面内子链接必须继续受 allow_domains 约束，不能绕过 source policy。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import RunMetrics, TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "industry_broad",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "_fetch_remote_pdf_text",
        lambda url, workspace_dir: (_ for _ in ()).throw(AssertionError("blocked PDF should not be fetched")),
        raising=False,
    )
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "DeepSeek V4 Preview Release",
                            "url": "https://api-docs.deepseek.com/news/news260424",
                            "snippet": "DeepSeek-V4 Preview is officially live.",
                        }
                    ],
                    fetch_fn=lambda url: {
                        "text": (
                            "<a href=\"https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/"
                            "blob/main/DeepSeek_V4.pdf\">Tech Report</a>"
                        ),
                        "mime_type": "text/html",
                    },
                )
            }
        ),
    )

    result = researcher.researcher_node(
        {
            "research_topic": "DeepSeek-V4 architecture",
            "research_profile": "benchmark",
            "source_profile": "industry_broad",
            "policy_overrides": {
                "allow_domains": ["api-docs.deepseek.com"],
                "budget": {"max_candidates_per_connector": 4, "max_fetches_per_task": 4, "max_total_fetches": 6},
            },
            "tasks": [
                TaskItem(
                    id=1,
                    title="DeepSeek-V4 官方信息",
                    intent="确认官方信息",
                    query="DeepSeek V4 Preview Release official",
                    task_type="research",
                    preferred_sources=["web"],
                    must_include_terms=["DeepSeek"],
                )
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "source_snapshots": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert [source.mime_type for source in result["sources_gathered"]] == ["text/html"]
    assert result["connector_health"]["open_web"]["policy_blocked"] == 1
    assert result["blocked_source_candidates"][0]["reason"] == "domain_not_allowed"


def test_researcher_reuses_existing_pdf_for_follow_up_without_empty_overwrite(tmp_path: Path, monkeypatch):
    """补采集遇到已抓取过的官方 PDF 时，应复用现有 source，而不是追加“暂无可用信息”。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import EvidenceNote, RunMetrics, TaskItem

    pdf_url = "https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf"
    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "industry_broad",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)

    class StaticLLM:
        def invoke(self, messages):
            return type("Response", (), {"content": "DeepSeek_V4.pdf confirms Muon and mHC. [5]"})()

    monkeypatch.setattr(researcher, "get_llm", lambda: StaticLLM())
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "pdf",
                            "title": "DeepSeek_V4.pdf",
                            "url": pdf_url,
                            "snippet": "DeepSeek-V4 technical report",
                        }
                    ],
                    fetch_fn=lambda url: (_ for _ in ()).throw(AssertionError("visited source should be reused")),
                )
            }
        ),
    )
    snapshot_dir = Path(settings.workspace_dir) / "snapshots"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "snapshot-pdf.txt").write_text(
        (
            "DeepSeek-V4 architecture overview. "
            "Muon Optimizer: DeepSeek-V4 introduces the Muon optimizer for faster convergence "
            "and greater training stability. mHC strengthens conventional residual connections."
        ),
        encoding="utf-8",
    )

    existing_source = SourceRecord(
        citation_id=5,
        source_id="source-5",
        source_type="pdf",
        query="DeepSeek-V4 Pro vs Flash",
        title="DeepSeek_V4.pdf",
        canonical_uri=pdf_url,
        url=pdf_url,
        snippet=(
            "DeepSeek-V4-Pro has 1.6T parameters and 49B activated. "
            "DeepSeek-V4-Flash has 284B parameters and 13B activated. "
            "The report describes MoE, CSA, HCA, mHC, the Muon optimizer, and 1M context."
        ),
        task_title="Pro与Flash版本差异化分析",
        snapshot_ref="snapshot-pdf",
        mime_type="application/pdf",
        trust_tier=4,
        selected=True,
    )

    result, has_more_work = researcher.collect_research_step(
        {
            "research_topic": "DeepSeek-V4 architecture",
            "research_profile": "default",
            "source_profile": "industry_broad",
            "policy_overrides": {
                "allow_domains": ["huggingface.co"],
                "budget": {"max_candidates_per_connector": 4, "max_fetches_per_task": 4, "max_total_fetches": 6},
            },
            "tasks": [
                TaskItem(
                    id=3,
                    title="Muon优化器与mHC架构设计",
                    intent="确认官方技术报告中的 Muon 和 mHC",
                    query="DeepSeek-V4 Muon optimizer mHC hierarchical computation 2025",
                    task_type="research",
                    preferred_sources=["web"],
                    must_include_terms=["Muon", "mHC"],
                )
            ],
            "task_summaries": ["## Muon优化器与mHC架构设计\n\n暂无可用信息。\n"],
            "sources_gathered": [existing_source],
            "source_snapshots": [],
            "visited_source_uris": [pdf_url],
            "search_results": [],
            "evidence_notes": [
                EvidenceNote(
                    task_id=3,
                    task_title="Muon优化器与mHC架构设计",
                    query="DeepSeek-V4 Muon optimizer mHC hierarchical computation 2025",
                    summary="## Muon优化器与mHC架构设计\n\n暂无可用信息。\n",
                    source_ids=[],
                    selected_source_ids=[],
                )
            ],
            "pending_follow_up_queries": [
                "DeepSeek-V4 Muon optimizer mHC hierarchical computation 2025 official technical report PDF evidence"
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert has_more_work is False
    assert len(result["evidence_notes"]) == 1
    assert result["evidence_notes"][0].selected_source_ids == [5]
    assert "暂无可用信息" not in result["task_summaries"][0]
    assert "DeepSeek_V4.pdf" in result["task_summaries"][0]
    assert "greater training stability" in result["sources_gathered"][0].snippet
    assert result["tasks"][0].status == "completed"


def test_researcher_uses_query_aware_snippet_for_fetched_web_text(tmp_path: Path, monkeypatch):
    """官方页面正文里较靠后的 API 信息应进入 source snippet，而不是只保留导航摘要。"""
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from legacy.workflows.states import RunMetrics, TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path / "workspace"),
            "source_policy_mode": "industry_broad",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)

    class StaticLLM:
        def invoke(self, messages):
            return type("Response", (), {"content": "API is available via OpenAI ChatCompletions. [1]"})()

    monkeypatch.setattr(researcher, "get_llm", lambda: StaticLLM())
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "DeepSeek V4 Preview Release",
                            "url": "https://api-docs.deepseek.com/news/news260424",
                            "snippet": "DeepSeek-V4 API OpenAI ChatCompletions deployment",
                        }
                    ],
                    fetch_fn=lambda url: {
                        "text": (
                            "Navigation Quick Start Pricing Guides Other Resources. "
                            "DeepSeek-V4 Preview is officially live. "
                            "API is Available Today. Keep base_url, just update model to "
                            "deepseek-v4-pro or deepseek-v4-flash. Supports OpenAI ChatCompletions."
                        ),
                        "mime_type": "text/html",
                    },
                )
            }
        ),
    )

    result = researcher.researcher_node(
        {
            "research_topic": "DeepSeek-V4 API boundary",
            "research_profile": "default",
            "source_profile": "industry_broad",
            "policy_overrides": {
                "allow_domains": ["api-docs.deepseek.com"],
                "budget": {"max_candidates_per_connector": 4, "max_fetches_per_task": 4, "max_total_fetches": 6},
            },
            "tasks": [
                TaskItem(
                    id=5,
                    title="推理部署模式与开源边界",
                    intent="确认 API 模式",
                    query="DeepSeek-V4 API OpenAI ChatCompletions deployment",
                    task_type="research",
                    preferred_sources=["web"],
                    must_include_terms=["API", "OpenAI", "ChatCompletions"],
                )
            ],
            "task_summaries": [],
            "sources_gathered": [],
            "source_snapshots": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert "API is Available Today" in result["sources_gathered"][0].snippet
    assert "Supports OpenAI ChatCompletions" in result["sources_gathered"][0].snippet


def test_phase3_orchestrator_persists_snapshots_under_job_dir(tmp_path: Path, monkeypatch):
    """公开 orchestrator 路径应把 snapshot 和 bundle sidecars 写入 job 目录。"""
    from artifacts.schemas import validate_instance
    from legacy.agents import researcher
    from connectors.legacy import LegacyConnectorAdapter
    from connectors.registry import ConnectorRegistry
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService
    from legacy.workflows.states import CriticFeedback, ReportArtifact, TaskItem

    settings = type(
        "Settings",
        (),
        {
            "enabled_sources": ["web"],
            "max_search_results": 5,
            "per_source_max_results": 4,
            "per_task_selected_sources": 4,
            "enabled_capability_types": ["builtin"],
            "skill_paths": [],
            "mcp_servers": [],
            "workspace_dir": str(tmp_path),
            "source_policy_mode": "trusted-web",
            "connector_substrate_enabled": True,
            "snapshot_store_dirname": "snapshots",
        },
    )()
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "_build_phase3_connector_registry",
        lambda _settings: ConnectorRegistry(
            {
                "open_web": LegacyConnectorAdapter(
                    source_name="web",
                    search_fn=lambda query, max_results=5: [
                        {
                            "source_type": "web",
                            "title": "LangGraph Docs",
                            "url": "https://docs.langchain.com/langgraph",
                            "snippet": "LangGraph helps build stateful agents.",
                        }
                    ],
                    fetch_fn=lambda url: {
                        "text": "LangGraph helps build stateful agents.",
                        "mime_type": "text/html",
                    },
                )
            }
        ),
    )

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(
        topic="LangGraph 是什么",
        max_loops=1,
        research_profile="benchmark",
        source_profile="trusted-web",
        start_worker=False,
    )
    orchestrator = ResearchJobOrchestrator(
        service=service,
        planner_fn=lambda state: {
            "tasks": [
                TaskItem(
                    id=1,
                    title="定义",
                    intent="解释概念",
                    query="LangGraph 是什么",
                    task_type="research",
                    expected_aspects=["LangGraph 是什么"],
                    preferred_sources=["web"],
                )
            ],
            "status": "planned",
        },
        collect_step_fn=researcher.collect_research_step,
        verifier_fn=lambda state: {
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": state.get("memory_stats"),
            "run_metrics": state.get("run_metrics"),
            "status": "verified",
        },
        critic_fn=lambda state: {
            "critic_feedback": CriticFeedback(
                quality_score=8,
                is_sufficient=True,
                gaps=[],
                follow_up_queries=[],
                feedback="已足够",
            ),
            "run_metrics": state.get("run_metrics"),
            "status": "reviewed",
        },
        writer_fn=lambda state: {
            "final_report": "# 报告\n\nLangGraph 是一个用于构建有状态 agent 的框架。[1]",
            "report_artifact": ReportArtifact(
                topic=state["research_topic"],
                report="# 报告\n\nLangGraph 是一个用于构建有状态 agent 的框架。[1]",
                citations=state["sources_gathered"],
                evidence_notes=state.get("evidence_notes", []),
                metrics=state.get("run_metrics", RunMetrics()),
            ),
            "status": "completed",
        },
    )

    final_job = orchestrator.run(job.job_id)

    job_snapshot_dir = Path(final_job.report_path).parent / "snapshots"
    workspace_snapshot_dir = tmp_path / "snapshots"
    bundle_dir = Path(final_job.report_bundle_path).parent
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    bundle = json.loads(Path(final_job.report_bundle_path).read_text(encoding="utf-8"))
    audit_decision = json.loads((bundle_dir / "audit_decision.json").read_text(encoding="utf-8"))

    assert list(job_snapshot_dir.glob("*.json"))
    assert list(job_snapshot_dir.glob("*.txt"))
    assert not list(workspace_snapshot_dir.glob("*.json"))
    assert Path(final_job.report_path).exists()
    assert (bundle_dir / "report.html").exists()
    assert (bundle_dir / "claims.json").exists()
    assert (bundle_dir / "sources.json").exists()
    assert (bundle_dir / "audit_decision.json").exists()
    assert (bundle_dir / "manifest.json").exists()
    validate_instance("report-bundle", bundle)
    validate_instance("artifact-manifest", manifest)
    assert manifest["artifacts"]["report_bundle"] == "bundle/report_bundle.json"
    assert audit_decision["gate_status"] == bundle["audit_summary"]["gate_status"]


def test_service_build_initial_state_preserves_file_inputs(tmp_path: Path):
    """service/internal path 应能把 file_inputs 放入初始 state。"""
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    state = service.build_initial_state(
        topic="分析本地文件",
        max_loops=2,
        research_profile="default",
        source_profile="public-then-private",
        policy_overrides={"allow_domains": ["docs.langchain.com"]},
        file_inputs=["/tmp/example.md"],
    )

    assert state["source_profile"] == "public-then-private"
    assert state["file_inputs"] == ["/tmp/example.md"]
