"""Benchmark runner 输出回归测试。"""

from __future__ import annotations

from pathlib import Path

def test_load_topics_local3_replaces_default_t06():
    """local3 主题集应包含 T06C，并保留 T01/T02。"""
    from evaluation.comparators import load_topics

    topics = load_topics(topic_set="local3")

    assert [topic.id for topic in topics] == ["T01", "T02", "T06C"]
    assert topics[-1].topic == "openclaw安装教程"


def test_load_topics_portfolio12_returns_12_topics_with_tutorial_and_comparison_mix():
    """portfolio12 应返回更完整的 12 题研究集。"""
    from evaluation.comparators import load_topics

    topics = load_topics(topic_set="portfolio12")

    assert len(topics) == 12
    ids = [topic.id for topic in topics]
    assert "T06C" in ids
    assert "T09" in ids
    assert "T10" in ids
    assert "T11" in ids
    assert "T12" in ids


def test_build_benchmark_summary_includes_quality_gate_and_rankings(tmp_path: Path):
    """benchmark summary 应输出主 scorecard、legacy 指标和新的排名。"""
    from scripts.run_benchmark import build_benchmark_summary, save_summary

    results = [
        {
            "topic_id": "T01",
            "topic": "主题1",
            "comparators": {
                "ours": {
                    "status": "completed",
                    "success": True,
                    "metrics": {
                        "word_count": 4200,
                        "source_coverage": 6,
                        "aspect_coverage": 0.8,
                        "citation_accuracy": 0.75,
                        "depth_score": 1.0,
                        "time_seconds": 120,
                        "judge_overall": None,
                        "judge_accuracy": None,
                        "judge_citation": None,
                        "quality_gate_passed": True,
                        "high_trust_aspect_score_100": 82.0,
                        "cross_source_corroboration_score_100": 76.0,
                        "verification_strength_score_100": 88.0,
                        "entity_resolution_score_100": 79.0,
                        "citation_alignment_score_100": 84.0,
                        "conflict_disclosure_score_100": None,
                        "quality_gate_margin_100": 81.0,
                        "coverage_balance_score_100": 77.0,
                        "structure_completeness_score_100": 92.0,
                        "evidence_novelty_score_100": 68.0,
                        "support_specificity_score_100": 79.0,
                        "recovery_resilience_score_100": 72.0,
                        "research_reliability_score_100": 82.0,
                        "system_controllability_score_100": 74.0,
                        "report_quality_score_100": 83.0,
                        "tool_use_success_rate": 0.8,
                        "fallback_search_calls": 0,
                        "search_calls": 10,
                    },
                }
            },
        },
        {
            "topic_id": "T02",
            "topic": "主题2",
            "comparators": {
                "ours": {
                    "status": "completed",
                    "success": True,
                    "metrics": {
                        "word_count": 3800,
                        "source_coverage": 5,
                        "aspect_coverage": 0.6,
                        "citation_accuracy": 0.7,
                        "depth_score": 0.9,
                        "time_seconds": 140,
                        "judge_overall": None,
                        "judge_accuracy": None,
                        "judge_citation": None,
                        "quality_gate_passed": False,
                        "high_trust_aspect_score_100": 66.0,
                        "cross_source_corroboration_score_100": 61.0,
                        "verification_strength_score_100": 72.0,
                        "entity_resolution_score_100": 69.0,
                        "citation_alignment_score_100": 70.0,
                        "conflict_disclosure_score_100": 50.0,
                        "quality_gate_margin_100": 69.0,
                        "coverage_balance_score_100": 62.0,
                        "structure_completeness_score_100": 78.0,
                        "evidence_novelty_score_100": 51.0,
                        "support_specificity_score_100": 63.0,
                        "recovery_resilience_score_100": 45.0,
                        "research_reliability_score_100": 64.0,
                        "system_controllability_score_100": 59.0,
                        "report_quality_score_100": 68.0,
                        "tool_use_success_rate": 0.5,
                        "fallback_search_calls": 2,
                        "search_calls": 8,
                    },
                }
            },
        },
    ]

    summary = build_benchmark_summary(results, comparator_name="ours")
    json_path, md_path = save_summary(summary, tmp_path)

    assert summary["counts"]["completed"] == 2
    assert summary["counts"]["quality_gate_passed"] == 1
    assert summary["judge_status"] == "skipped"
    assert summary["rankings"]["by_research_reliability_score_100"] == ["T01", "T02"]
    assert summary["scorecard"]["research_reliability_score_100"]["avg"] == 73.0
    assert summary["legacy_metrics"]["citation_accuracy"]["avg"] == 0.725
    assert summary["benchmark_health"]["judge_status"] == "skipped"
    assert summary["benchmark_health"]["completion_rate_100"] == 100.0
    assert summary["benchmark_health"]["quality_gate_pass_rate_100"] == 50.0
    assert json_path.exists()
    assert md_path.exists()
    assert "Reliability" in md_path.read_text(encoding="utf-8")
