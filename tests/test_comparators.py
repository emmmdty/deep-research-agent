"""Comparator registry 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

from configs.settings import Settings


def test_load_topics_returns_structured_topics():
    """标准 benchmark 主题应解析为结构化对象。"""
    from evaluation.comparators import BenchmarkTopic, load_topics

    topics = load_topics(max_topics=2)

    assert len(topics) == 2
    assert all(isinstance(topic, BenchmarkTopic) for topic in topics)
    assert topics[0].expected_aspects


def test_resolve_comparators_merges_optional_entries():
    """显式传入的可选 comparator 应拼接到启用列表末尾。"""
    from evaluation.comparators import resolve_comparators

    settings = Settings(enabled_comparators="ours,gptr")

    assert resolve_comparators(settings, include_optional=["gemini", "gptr"]) == [
        "ours",
        "gptr",
        "gemini",
    ]


def test_import_report_comparator_reads_markdown_and_meta(tmp_path: Path):
    """报告导入 comparator 应能读取 Markdown 和元数据。"""
    from evaluation.comparators import BenchmarkTopic, run_import_report_comparator

    report_dir = tmp_path / "alibaba"
    report_dir.mkdir()
    (report_dir / "T01.md").write_text("# 报告\n\n内容 [1]", encoding="utf-8")
    (report_dir / "T01_meta.json").write_text(
        json.dumps({"time_seconds": 12.5, "status": "completed"}),
        encoding="utf-8",
    )

    topic = BenchmarkTopic(
        id="T01",
        topic="测试主题",
        expected_aspects=["内容"],
        min_sources=1,
        min_words=10,
    )
    result = run_import_report_comparator(
        name="alibaba",
        topic=topic,
        report_dir=report_dir,
    )

    assert result.status == "completed"
    assert result.success is True
    assert result.report_text.startswith("# 报告")
    assert result.metrics["time_seconds"] == 12.5
    assert result.report_path.endswith("T01.md")


def test_run_comparator_skips_when_optional_comparator_not_configured(monkeypatch, tmp_path: Path):
    """缺少配置的可选 comparator 应返回 skipped，而不是抛异常。"""
    from evaluation.comparators import BenchmarkTopic, run_comparator

    topic = BenchmarkTopic(
        id="T02",
        topic="另一个测试主题",
        expected_aspects=[],
        min_sources=1,
        min_words=10,
    )
    settings = Settings(
        gemini_enabled=False,
        gemini_command=None,
        gemini_report_dir=None,
        workspace_dir=str(tmp_path / "workspace"),
    )
    monkeypatch.setattr("evaluation.comparators.get_settings", lambda: settings)

    result = run_comparator(
        name="gemini",
        topic=topic,
        output_root=tmp_path / "outputs",
    )

    assert result.status == "skipped"
    assert result.success is False
    assert "gemini" in result.error.lower()


def test_run_ours_comparator_marks_failed_quality_gate_as_failed(monkeypatch, tmp_path: Path):
    """严格 quality gate 失败时，ours comparator 不应再伪装成 completed。"""
    from evaluation.comparators import BenchmarkTopic, run_ours_comparator
    from legacy.workflows.states import RunMetrics

    topic = BenchmarkTopic(
        id="T01",
        topic="测试主题",
        expected_aspects=["行业应用案例"],
        min_sources=1,
        min_words=10,
    )

    monkeypatch.setattr(
        "legacy.workflows.graph.run_research",
        lambda *args, **kwargs: {
            "status": "failed_quality_gate",
            "error": "缺少真实案例证据",
            "final_report": None,
            "report_artifact": None,
            "sources_gathered": [],
            "run_metrics": RunMetrics(
                status="failed_quality_gate",
                quality_gate_status="failed",
                quality_gate_fail_reason="缺少真实案例证据",
            ),
        },
    )

    result = run_ours_comparator(
        topic,
        tmp_path / "outputs",
        max_loops=2,
        research_profile="benchmark",
    )

    assert result.status == "failed"
    assert result.success is False
    assert result.metrics["quality_gate_status"] == "failed"
    assert result.metrics["quality_gate_fail_reason"] == "缺少真实案例证据"
    assert "真实案例" in result.error
