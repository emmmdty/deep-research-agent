"""Verifier 与证据记忆回归测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from legacy.workflows.states import EvidenceNote, RunMetrics, SourceRecord


def test_verifier_node_builds_clusters_and_persists_memory(tmp_path: Path, monkeypatch):
    """Verifier 应把来源转成证据并落到持久化记忆中。"""
    from legacy.agents import verifier

    settings = SimpleNamespace(workspace_dir=str(tmp_path / "workspace"))
    monkeypatch.setattr(verifier, "get_settings", lambda: settings)

    result = verifier.verifier_node(
        {
            "research_topic": "RAG 技术的原理和应用",
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_type="github",
                    query="RAG 基本原理",
                    title="LangChain RAG guide",
                    url="https://github.com/langchain-ai/langchain",
                    snippet="RAG combines retrieval and generation to reduce hallucination.",
                    task_title="定义与原理",
                    trust_tier=5,
                    selected=True,
                ),
                SourceRecord(
                    citation_id=2,
                    source_type="arxiv",
                    query="RAG 基本原理",
                    title="RAG paper",
                    url="https://arxiv.org/abs/2005.11401",
                    snippet="Retrieval-augmented generation improves factual grounding.",
                    task_title="定义与原理",
                    trust_tier=4,
                    selected=True,
                ),
            ],
            "evidence_notes": [
                EvidenceNote(
                    task_id=1,
                    task_title="定义与原理",
                    query="RAG 基本原理",
                    summary="### 核心结论\n\nRAG 结合检索与生成。[1][2]",
                    source_ids=[1, 2],
                    selected_source_ids=[1, 2],
                )
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["memory_stats"].total_evidence_units == 2
    assert result["memory_stats"].total_clusters >= 1
    assert result["verification_records"]
    assert (tmp_path / "workspace" / "memory" / "evidence.db").exists()


def test_verifier_node_detects_entity_drift_for_conflicting_sources(tmp_path: Path, monkeypatch):
    """当同一主题出现相互冲突的实体定义时，Verifier 应降低一致性分数。"""
    from legacy.agents import verifier

    settings = SimpleNamespace(workspace_dir=str(tmp_path / "workspace"))
    monkeypatch.setattr(verifier, "get_settings", lambda: settings)

    result = verifier.verifier_node(
        {
            "research_topic": "openclaw安装教程",
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_type="github",
                    query="openclaw install",
                    title="OpenClaw game engine",
                    url="https://github.com/opentomb/OpenClaw",
                    snippet="OpenClaw is an open source Captain Claw game engine.",
                    task_title="安装步骤",
                    trust_tier=5,
                    selected=True,
                ),
                SourceRecord(
                    citation_id=2,
                    source_type="web",
                    query="openclaw install",
                    title="OpenClaw AI Agent setup",
                    url="https://ai.example.com/openclaw-agent",
                    snippet="OpenClaw is a personal AI agent with chat memory and plugins.",
                    task_title="安装步骤",
                    trust_tier=2,
                    selected=True,
                ),
            ],
            "evidence_notes": [
                EvidenceNote(
                    task_id=1,
                    task_title="安装步骤",
                    query="openclaw install",
                    summary="### 核心结论\n\nOpenClaw 安装依赖 SDL2。[1]\n\n### 补充观察\n\n也有来源将 OpenClaw 描述为 AI Agent。[2]",
                    source_ids=[1, 2],
                    selected_source_ids=[1, 2],
                )
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["memory_stats"].entity_consistency_score < 1.0
    assert result["memory_stats"].conflict_count >= 1
    assert any(record.status == "weakly_supported" for record in result["verification_records"])


def test_verifier_node_ignores_general_sources_when_scoring_entity_consistency(tmp_path: Path, monkeypatch):
    """中性来源不应把单一主实体的可信度拉低。"""
    from legacy.agents import verifier

    settings = SimpleNamespace(workspace_dir=str(tmp_path / "workspace"))
    monkeypatch.setattr(verifier, "get_settings", lambda: settings)

    result = verifier.verifier_node(
        {
            "research_topic": "openclaw安装教程",
            "sources_gathered": [
                SourceRecord(
                    citation_id=1,
                    source_type="web",
                    query="openclaw install",
                    title="OpenClaw AI assistant",
                    url="https://docs.openclaw.ai/install",
                    snippet="OpenClaw installs as a personal AI assistant.",
                    task_title="安装步骤",
                    trust_tier=4,
                    selected=True,
                ),
                SourceRecord(
                    citation_id=2,
                    source_type="web",
                    query="openclaw install",
                    title="Install | OpenClaw Docs",
                    url="https://docs.openclaw.ai/start/getting-started",
                    snippet="Install OpenClaw on Windows and Linux with the recommended script.",
                    task_title="安装步骤",
                    trust_tier=4,
                    selected=True,
                ),
            ],
            "evidence_notes": [
                EvidenceNote(
                    task_id=1,
                    task_title="安装步骤",
                    query="openclaw install",
                    summary="### 核心结论\n\nOpenClaw 安装使用官方脚本。[1][2]",
                    source_ids=[1, 2],
                    selected_source_ids=[1, 2],
                )
            ],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["memory_stats"].entity_consistency_score == 1.0
    assert result["memory_stats"].conflict_count == 0
