"""Phase 04 claim-level audit pipeline 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from workflows.states import EvidenceNote, ReportArtifact, RunMetrics, SourceRecord, TaskItem


PHASE4_SCHEMA_NAMES = [
    "critical-claim-review-item",
    "claim-review-queue",
]


@pytest.mark.parametrize("schema_name", PHASE4_SCHEMA_NAMES)
def test_phase4_schema_files_exist_and_are_loadable(schema_name: str):
    """Phase 04 新增 schema 应存在且可加载。"""
    from artifacts.schemas import load_schema

    schema = load_schema(schema_name)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"


def test_claim_review_queue_schema_requires_items():
    """review queue schema 缺少 items 时应失败。"""
    from artifacts.schemas import validate_instance

    payload = {
        "job_id": "job-phase4-001",
        "created_at": "2026-04-09T00:00:00+00:00",
    }

    with pytest.raises(ValidationError):
        validate_instance("claim-review-queue", payload)


def test_claim_auditor_builds_blocked_review_queue_for_critical_claim():
    """critical claim 无法被证据支撑时，应进入 blocked review queue。"""
    from auditor.pipeline import claim_auditor_node

    result = claim_auditor_node(
        {
            "research_topic": "LangGraph 是什么",
            "tasks": [
                TaskItem(
                    id=1,
                    title="定义",
                    intent="解释概念",
                    query="LangGraph 是什么",
                    status="completed",
                )
            ],
            "task_summaries": ["### 核心结论\n\nLangGraph 不是一个用于状态化 agent 的框架。[1]"],
            "evidence_notes": [
                EvidenceNote(
                    task_id=1,
                    task_title="定义",
                    query="LangGraph 是什么",
                    summary="### 核心结论\n\nLangGraph 不是一个用于状态化 agent 的框架。[1]",
                    source_ids=[1],
                    selected_source_ids=[1],
                    claim_count=1,
                )
            ],
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_id="source-1",
                    source_type="web",
                    query="LangGraph 是什么",
                    title="LangGraph Docs",
                    canonical_uri="https://docs.langchain.com/langgraph",
                    url="https://docs.langchain.com/langgraph",
                    snippet="LangGraph is a framework for building stateful, long-running agents.",
                    snapshot_ref="snapshot-1",
                    task_title="定义",
                    selected=True,
                    trust_tier=5,
                )
            ],
            "evidence_fragments": [
                {
                    "evidence_id": "evidence-1",
                    "snapshot_id": "snapshot-1",
                    "source_id": "source-1",
                    "locator": {"kind": "snippet", "citation_id": 1},
                    "excerpt": "LangGraph is a framework for building stateful, long-running agents.",
                    "extraction_method": "source_snippet",
                }
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["status"] == "claim_audited"
    assert result["audit_gate_status"] == "blocked"
    assert result["critical_claim_review_queue"]
    assert result["blocked_critical_claim_count"] == 1
    assert result["claims"][0].placeholder is False
    assert result["claims"][0].status in {"contradicted", "unsupported", "unverifiable"}
    assert result["claim_support_edges"]
    assert result["claim_support_edges"][0].source_id == "source-1"
    assert result["claim_support_edges"][0].snapshot_id == "snapshot-1"
    assert result["claim_support_edges"][0].locator == {"kind": "snippet", "citation_id": 1}
    assert result["claim_support_edges"][0].grounding_status == "grounded"


def test_claim_auditor_blocks_supported_critical_claim_without_snapshot_grounding():
    """看似 supported 但缺少 snapshot grounding 的 critical claim 必须 blocked。"""
    from auditor.pipeline import claim_auditor_node

    result = claim_auditor_node(
        {
            "research_topic": "LangGraph 是什么",
            "tasks": [
                TaskItem(
                    id=1,
                    title="定义",
                    intent="解释概念",
                    query="LangGraph 是什么",
                    status="completed",
                )
            ],
            "task_summaries": ["### 核心结论\n\nLangGraph 是一个支持状态化 agent 的框架。[1]"],
            "evidence_notes": [
                EvidenceNote(
                    task_id=1,
                    task_title="定义",
                    query="LangGraph 是什么",
                    summary="### 核心结论\n\nLangGraph 是一个支持状态化 agent 的框架。[1]",
                    source_ids=[1],
                    selected_source_ids=[1],
                    claim_count=1,
                )
            ],
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_id="source-1",
                    source_type="web",
                    query="LangGraph 是什么",
                    title="LangGraph Docs",
                    canonical_uri="https://docs.langchain.com/langgraph",
                    url="https://docs.langchain.com/langgraph",
                    snippet="LangGraph is a framework for building stateful agents.",
                    snapshot_ref="",
                    task_title="定义",
                    selected=True,
                    trust_tier=5,
                )
            ],
            "evidence_fragments": [
                {
                    "evidence_id": "evidence-1",
                    "snapshot_id": "",
                    "source_id": "source-1",
                    "locator": {"kind": "snippet", "citation_id": 1},
                    "excerpt": "LangGraph is a framework for building stateful agents.",
                    "extraction_method": "source_snippet",
                }
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["audit_gate_status"] == "blocked"
    assert result["blocked_critical_claim_count"] == 1
    assert result["claims"][0].status == "unverifiable"
    assert result["claim_support_edges"][0].relation == "supports"
    assert result["claim_support_edges"][0].grounding_status == "missing_snapshot"
    assert result["critical_claim_review_queue"][0].reason == "critical_claim_unverifiable"
    assert result["critical_claim_review_queue"][0].edge_ids == ["edge-1"]


def test_orchestrator_runs_claim_auditing_stage_and_emits_blocked_bundle(tmp_path: Path):
    """orchestrator 应经过 claim_auditing 阶段，并保留 completed+blocked 语义。"""
    from services.research_jobs.orchestrator import ResearchJobOrchestrator
    from services.research_jobs.service import ResearchJobService

    service = ResearchJobService(workspace_dir=str(tmp_path))
    job = service.submit(topic="phase4 blocked path", max_loops=1, research_profile="default", start_worker=False)

    source = SourceRecord(
        citation_id=1,
        source_id="source-1",
        source_type="web",
        query="phase4 blocked path",
        title="LangGraph Docs",
        canonical_uri="https://docs.langchain.com/langgraph",
        url="https://docs.langchain.com/langgraph",
        snippet="LangGraph supports long-running, stateful agent workflows.",
        snapshot_ref="snapshot-1",
        task_title="定义",
        selected=True,
        trust_tier=5,
    )

    orchestrator = ResearchJobOrchestrator(
        service=service,
        planner_fn=lambda state: {
            "tasks": [TaskItem(id=1, title="定义", intent="解释概念", query="phase4 blocked path", status="pending")],
            "status": "planned",
        },
        collect_step_fn=lambda state: (
            {
                "tasks": [
                    TaskItem(
                        id=1,
                        title="定义",
                        intent="解释概念",
                        query="phase4 blocked path",
                        status="completed",
                        summary="### 核心结论\n\nLangGraph 不支持状态化 agent。[1]",
                        sources="[1]",
                    )
                ],
                "task_summaries": ["### 核心结论\n\nLangGraph 不支持状态化 agent。[1]"],
                "sources_gathered": [source],
                "evidence_notes": [
                    EvidenceNote(
                        task_id=1,
                        task_title="定义",
                        query="phase4 blocked path",
                        summary="### 核心结论\n\nLangGraph 不支持状态化 agent。[1]",
                        source_ids=[1],
                        selected_source_ids=[1],
                        claim_count=1,
                    )
                ],
                "status": "researched",
            },
            False,
        ),
        verifier_fn=lambda state: {
            "evidence_fragments": [
                {
                    "evidence_id": "evidence-1",
                    "snapshot_id": "snapshot-1",
                    "source_id": "source-1",
                    "locator": {"kind": "snippet", "citation_id": 1},
                    "excerpt": "LangGraph supports long-running, stateful agent workflows.",
                    "extraction_method": "source_snippet",
                }
            ],
            "evidence_units": [],
            "evidence_clusters": [],
            "verification_records": [],
            "memory_stats": state.get("memory_stats"),
            "run_metrics": state.get("run_metrics"),
            "status": "verified",
        },
        claim_auditor_fn=lambda state: {
            "claims": [
                {
                    "claim_id": "claim-1",
                    "text": "LangGraph 不支持状态化 agent。",
                    "criticality": "high",
                    "uncertainty": "low",
                    "status": "contradicted",
                    "placeholder": False,
                    "section_ref": "定义",
                    "evidence_ids": ["evidence-1"],
                }
            ],
            "claim_support_edges": [
                {
                    "edge_id": "edge-1",
                    "claim_id": "claim-1",
                    "evidence_id": "evidence-1",
                    "relation": "contradicts",
                    "confidence": 0.95,
                    "notes": "正文 claim 与证据片段方向相反。",
                }
            ],
            "conflict_sets": [
                {
                    "conflict_id": "conflict-1",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                    "status": "open",
                    "summary": "关键 claim 与直接证据冲突。",
                }
            ],
            "critical_claim_review_queue": [
                {
                    "review_id": "review-1",
                    "claim_id": "claim-1",
                    "text": "LangGraph 不支持状态化 agent。",
                    "status": "blocked",
                    "reason": "critical_claim_contradicted",
                    "blocking": True,
                    "evidence_ids": ["evidence-1"],
                    "edge_ids": ["edge-1"],
                }
            ],
            "audit_gate_status": "blocked",
            "blocked_critical_claim_count": 1,
            "critical_claim_count": 1,
            "status": "claim_audited",
        },
        writer_fn=lambda state: {
            "final_report": "# 报告\n\n存在未通过审核的关键结论。\n",
            "report_artifact": ReportArtifact(
                topic=state["research_topic"],
                report="# 报告\n\n存在未通过审核的关键结论。\n",
                citations=[source],
                evidence_notes=state["evidence_notes"],
                metrics=RunMetrics(status="completed"),
            ),
            "status": "completed",
        },
    )

    final_job = orchestrator.run(job.job_id)
    events = service.list_events(job.job_id)
    bundle = json.loads(Path(final_job.report_bundle_path).read_text(encoding="utf-8"))

    assert final_job.status == "completed"
    assert final_job.audit_gate_status == "blocked"
    assert any(event.stage == "claim_auditing" and event.event_type == "stage.completed" for event in events)
    assert bundle["audit_summary"]["gate_status"] == "blocked"
    assert bundle["claims"][0]["placeholder"] is False
    assert bundle["claim_support_edges"]
    assert bundle["conflict_sets"]


def test_build_report_bundle_preserves_audited_claim_graph():
    """bundle 构建器应优先输出 phase04 的真实 claim graph。"""
    from artifacts.bundle import build_report_bundle

    result = {
        "research_topic": "LangGraph",
        "research_profile": "default",
        "status": "completed",
        "audit_gate_status": "blocked",
        "critical_claim_count": 1,
        "blocked_critical_claim_count": 1,
        "final_report": "# 报告\n\n存在待复核关键结论。[1]",
        "sources_gathered": [
            {
                "citation_id": 1,
                "source_id": "source-1",
                "source_type": "web",
                "query": "LangGraph",
                "title": "LangGraph Docs",
                "canonical_uri": "https://docs.langchain.com/langgraph",
                "url": "https://docs.langchain.com/langgraph",
                "snippet": "LangGraph supports stateful agents.",
                "snapshot_ref": "snapshot-real-1",
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
        "evidence_fragments": [
            {
                "evidence_id": "evidence-1",
                "snapshot_id": "snapshot-real-1",
                "source_id": "source-1",
                "locator": {"kind": "snippet"},
                "excerpt": "LangGraph supports stateful agents.",
                "extraction_method": "source_snippet",
            }
        ],
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "LangGraph 不支持状态化 agent。",
                "criticality": "high",
                "uncertainty": "low",
                "status": "contradicted",
                "placeholder": False,
                "section_ref": "定义",
                "evidence_ids": ["evidence-1"],
            }
        ],
        "claim_support_edges": [
            {
                "edge_id": "edge-1",
                "claim_id": "claim-1",
                "evidence_id": "evidence-1",
                "relation": "contradicts",
                "confidence": 0.95,
                "notes": "方向相反。",
                "source_id": "source-1",
                "snapshot_id": "snapshot-real-1",
                "locator": {"kind": "snippet"},
                "grounding_status": "grounded",
            }
        ],
        "conflict_sets": [
            {
                "conflict_id": "conflict-1",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
                "status": "open",
                "summary": "关键 claim 与证据冲突。",
            }
        ],
        "run_metrics": {"llm_calls": 1, "search_calls": 1},
    }

    bundle = build_report_bundle(
        result,
        job_id="job-phase4-001",
        max_loops=2,
        research_profile="default",
        source_profile="trusted-web",
        report_bundle_ref="bundle/report_bundle.json",
        trace_events=[],
        runtime_path="orchestrator-v1",
    )

    assert bundle["audit_summary"]["gate_status"] == "blocked"
    assert bundle["claims"][0]["placeholder"] is False
    assert bundle["claim_support_edges"][0]["relation"] == "contradicts"
    assert bundle["claim_support_edges"][0]["snapshot_id"] == "snapshot-real-1"
    assert bundle["conflict_sets"][0]["conflict_id"] == "conflict-1"

    from artifacts.schemas import validate_instance

    validate_instance("report-bundle", bundle)


def test_phase4_metrics_helpers_use_claim_graph():
    """phase04 指标 helper 应读取 claim graph，而不是回退到 report-shape 指标。"""
    from evaluation.metrics import (
        conflict_detection_recall,
        critical_claim_support_precision,
        provenance_completeness,
        unsupported_critical_claim_leakage,
    )

    artifact = ReportArtifact(
        topic="LangGraph",
        report="# 报告\n\n存在待复核关键结论。",
        claims=[
            {
                "claim_id": "claim-1",
                "text": "LangGraph 不支持状态化 agent。",
                "criticality": "high",
                "uncertainty": "low",
                "status": "contradicted",
                "placeholder": False,
                "section_ref": "定义",
                "evidence_ids": ["evidence-1"],
            },
            {
                "claim_id": "claim-2",
                "text": "LangGraph 是一个框架。",
                "criticality": "medium",
                "uncertainty": "low",
                "status": "supported",
                "placeholder": False,
                "section_ref": "定义",
                "evidence_ids": ["evidence-2"],
            },
        ],
        claim_support_edges=[
            {
                "edge_id": "edge-1",
                "claim_id": "claim-1",
                "evidence_id": "evidence-1",
                "relation": "contradicts",
                "confidence": 0.95,
                "notes": "方向相反。",
            }
        ],
        conflict_sets=[
            {
                "conflict_id": "conflict-1",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
                "status": "open",
                "summary": "关键 claim 与证据冲突。",
            }
        ],
    )

    assert critical_claim_support_precision(artifact) == 0.0
    assert unsupported_critical_claim_leakage(artifact) == 1.0
    assert provenance_completeness(artifact) == 1.0
    assert conflict_detection_recall(artifact) == 1.0
