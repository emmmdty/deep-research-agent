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
