"""Ablation 脚本与内部 comparator 回归测试。"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.comparators import BenchmarkTopic, ComparatorResult


def test_resolve_comparators_supports_internal_ablation_variants():
    """内部 ablation variants 应能被 comparator resolver 识别。"""
    from configs.settings import get_settings
    from evaluation.comparators import resolve_comparators

    settings = get_settings()
    resolved = resolve_comparators(settings, requested=["ours_base", "ours_verifier", "ours_gate", "ours_full"])

    assert resolved == ["ours_base", "ours_verifier", "ours_gate", "ours_full"]


def test_run_ablation_writes_json_markdown_and_csv(monkeypatch, tmp_path: Path):
    """run_ablation 应输出实验结果、摘要和变体对比 CSV。"""
    from scripts import run_ablation

    topic = BenchmarkTopic(
        id="T01",
        topic="测试主题",
        expected_aspects=["方面A"],
        min_sources=1,
        min_words=10,
    )

    def fake_load_topics(topic_set="portfolio12", max_topics=0, topics_path=None):
        return [topic]

    def fake_run_comparator(name, topic, output_root, max_loops=2, research_profile="benchmark", settings=None, ablation_variant=None):
        reliability = {
            "ours_base": 58.0,
            "ours_verifier": 69.0,
            "ours_gate": 74.0,
            "ours_full": 82.0,
        }[name]
        gate_passed = name in {"ours_gate", "ours_full"}
        return ComparatorResult(
            name=name,
            status="completed",
            success=True,
            report_text="# 报告\n\n内容 [1]",
            metrics={
                "research_reliability_score_100": reliability,
                "system_controllability_score_100": reliability - 10,
                "report_quality_score_100": reliability + 5,
                "quality_gate_passed": gate_passed,
                "time_seconds": 10 + reliability / 10,
            },
            report_path=str(output_root / name / f"{topic.id}.md"),
        )

    monkeypatch.setattr(run_ablation, "load_topics", fake_load_topics)
    monkeypatch.setattr(run_ablation, "run_comparator", fake_run_comparator)

    outcome = run_ablation.run_ablation(
        output_root=tmp_path,
        topic_set="portfolio12",
        max_topics=1,
        max_loops=2,
        use_judge=False,
        research_profile="benchmark",
    )

    assert outcome["variants"] == ["ours_base", "ours_verifier", "ours_gate", "ours_full"]
    assert (tmp_path / "ablation_results.json").exists()
    assert (tmp_path / "ablation_summary.md").exists()
    assert (tmp_path / "variant_comparison.csv").exists()

    saved = json.loads((tmp_path / "ablation_results.json").read_text(encoding="utf-8"))
    assert saved["topics"][0]["comparators"]["ours_full"]["metrics"]["research_reliability_score_100"] == 82.0
    assert "ours_full" in (tmp_path / "ablation_summary.md").read_text(encoding="utf-8")
