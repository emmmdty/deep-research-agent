"""local3 自动优化脚本回归测试。"""

from __future__ import annotations

import json
from pathlib import Path


def test_optimize_local3_runs_multiple_rounds_until_thresholds_met(monkeypatch, tmp_path: Path):
    """当首轮未达标时，应输出分析文件并继续到下一轮。"""
    from scripts import optimize_local3

    topic_payload = {
        "topic_id": "T01",
        "topic": "测试主题",
        "comparators": {
            "ours": {
                "name": "ours",
                "status": "completed",
                "success": True,
                "report_text": "# 报告\n\n内容 [1]",
                "metrics": {},
                "sources": [],
            }
        },
    }

    round_results = [
        [topic_payload],
        [topic_payload],
    ]
    round_summaries = [
        {
            "counts": {"completed": 3, "failed": 0, "quality_gate_passed": 1},
            "aggregates": {"aspect_coverage": {"avg": 0.7}},
        },
        {
            "counts": {"completed": 3, "failed": 0, "quality_gate_passed": 3},
            "aggregates": {"aspect_coverage": {"avg": 0.9}},
        },
    ]

    def fake_run_benchmark_suite(**kwargs):
        return round_results.pop(0)

    def fake_build_benchmark_summary(results, comparator_name="ours"):
        return round_summaries.pop(0)

    monkeypatch.setattr(optimize_local3, "load_topics", lambda topic_set="local3", max_topics=0: [])
    monkeypatch.setattr(optimize_local3, "run_benchmark_suite", fake_run_benchmark_suite)
    monkeypatch.setattr(optimize_local3, "build_benchmark_summary", fake_build_benchmark_summary)

    outcome = optimize_local3.run_optimization(
        output_root=tmp_path,
        max_rounds=3,
        max_loops=2,
        skip_judge=True,
    )

    assert outcome["completed_rounds"] == 2
    assert outcome["thresholds_met"] is True
    assert (tmp_path / "round-1" / "failure_analysis.json").exists()
    assert (tmp_path / "round-1" / "strategy_patch_plan.json").exists()
    assert (tmp_path / "round-2" / "benchmark_summary.json").exists()


def test_build_failure_analysis_extracts_quality_and_aspect_failures(tmp_path: Path):
    """failure analysis 应汇总未达标主题的关键信号。"""
    from scripts.optimize_local3 import build_failure_analysis

    results = [
        {
            "topic_id": "T06C",
            "topic": "openclaw安装教程",
            "comparators": {
                "ours": {
                    "status": "completed",
                    "success": True,
                    "metrics": {
                        "aspect_coverage": 0.6,
                        "quality_gate_passed": False,
                        "quality_gate_status": "failed",
                        "high_trust_source_ratio": 0.33,
                        "entity_consistency_score": 0.7,
                        "off_topic_reject_count": 2,
                    },
                    "report_text": "# openclaw安装教程\n\n内容 [1]",
                }
            },
        }
    ]
    summary = {
        "counts": {"completed": 1, "failed": 0, "quality_gate_passed": 0},
        "aggregates": {"aspect_coverage": {"avg": 0.6}},
    }

    analysis = build_failure_analysis(results=results, summary=summary, output_root=tmp_path)

    assert analysis["failing_topics"][0]["topic_id"] == "T06C"
    assert analysis["failing_topics"][0]["quality_gate_fail_reason"] == "failed"
    assert analysis["failing_topics"][0]["high_trust_source_ratio"] == 0.33
    assert analysis["failing_topics"][0]["entity_consistency_score"] == 0.7
    saved = json.loads((tmp_path / "failure_analysis.json").read_text(encoding="utf-8"))
    assert saved["failing_topics"][0]["off_topic_reject_count"] == 2

