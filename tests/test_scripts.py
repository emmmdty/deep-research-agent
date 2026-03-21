"""Benchmark / comparison 脚本回归测试。"""

from __future__ import annotations

import os
from pathlib import Path

from evaluation.comparators import BenchmarkTopic, ComparatorResult


class _FakeJudge:
    """测试用 LLM Judge。"""

    def score_report(self, report: str, topic: str = "") -> dict:
        return {
            "overall": 8.5,
            "depth": 8,
            "accuracy": 9,
            "coherence": 8,
            "citation_quality": 8,
            "structure": 9,
            "comments": f"topic={topic}",
        }

    def compare_reports(self, report_a: str, report_b: str, topic: str = "") -> dict:
        return {
            "topic": topic,
            "report_a": {"overall": 8.8},
            "report_b": {"overall": 7.9},
            "winner": "A",
            "score_diff": 0.9,
            "reason": "A 更完整",
        }


def test_run_benchmark_suite_keeps_running_after_single_comparator_failure(monkeypatch, tmp_path: Path):
    """单个 comparator 失败时，benchmark 聚合不应中断。"""
    from scripts import run_benchmark

    topic = BenchmarkTopic(
        id="T01",
        topic="测试主题",
        expected_aspects=["性能", "成本"],
        min_sources=1,
        min_words=10,
    )

    def fake_run_comparator(name, topic, output_root, max_loops=2):
        if name == "gptr":
            return ComparatorResult(
                name=name,
                status="failed",
                success=False,
                error="runner exploded",
            )
        return ComparatorResult(
            name=name,
            status="completed",
            success=True,
            report_text="# 报告\n\n性能分析 [1]\n\n成本分析 [2]",
            metrics={"time_seconds": 3.2, "llm_calls": 4, "search_calls": 2},
            report_path=str(output_root / name / f"{topic.id}.md"),
        )

    monkeypatch.setattr(run_benchmark, "run_comparator", fake_run_comparator)
    monkeypatch.setattr(run_benchmark, "LLMJudge", lambda: _FakeJudge())

    results = run_benchmark.run_benchmark_suite(
        topics=[topic],
        comparator_names=["ours", "gptr"],
        output_root=tmp_path,
        use_judge=True,
    )

    assert len(results) == 1
    comparators = results[0]["comparators"]
    assert comparators["ours"]["status"] == "completed"
    assert comparators["ours"]["metrics"]["aspect_coverage"] == 1.0
    assert comparators["gptr"]["status"] == "failed"


def test_generate_comparison_markdown_includes_optional_skipped_result():
    """comparison 报告应保留 skipped comparator，避免信息丢失。"""
    from scripts.full_comparison import generate_comparison_report

    report = generate_comparison_report(
        [
            {
                "topic_id": "T01",
                "topic": "测试主题",
                "comparators": {
                    "ours": {"status": "completed", "metrics": {"judge_overall": 8.5}},
                    "gemini": {"status": "skipped", "error": "allowlist required", "metrics": {}},
                },
                "pairwise": {"gemini": {"winner": "A", "score_diff": 1.0}},
            }
        ]
    )

    assert "gemini" in report.lower()
    assert "skipped" in report.lower()
    assert "allowlist required" in report


def test_run_benchmark_suite_can_load_external_env_file(monkeypatch, tmp_path: Path):
    """benchmark runner 应支持从外部 env 文件加载运行配置。"""
    from configs.settings import get_settings, reset_settings
    from scripts import run_benchmark

    env_file = tmp_path / "benchmark.env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=minimax",
                "LLM_MODEL_NAME=MiniMax-M2.5",
                "LLM_API_KEY=test-benchmark-key",
                "LLM_BASE_URL=https://api.minimaxi.com/v1",
                "SEARCH_BACKEND=duckduckgo",
            ]
        ),
        encoding="utf-8",
    )
    reset_settings()

    topic = BenchmarkTopic(
        id="T01",
        topic="测试主题",
        expected_aspects=["性能"],
        min_sources=1,
        min_words=10,
    )

    def fake_run_comparator(name, topic, output_root, max_loops=2, research_profile="benchmark"):
        return ComparatorResult(
            name=name,
            status="completed",
            success=True,
            report_text="# 报告\n\n性能分析 [1]",
            metrics={"time_seconds": 1.0},
            report_path=str(output_root / name / f"{topic.id}.md"),
        )

    monkeypatch.setattr(run_benchmark, "run_comparator", fake_run_comparator)
    monkeypatch.setattr(run_benchmark, "LLMJudge", lambda: _FakeJudge())

    run_benchmark.run_benchmark_suite(
        topics=[topic],
        comparator_names=["ours"],
        output_root=tmp_path / "out",
        use_judge=True,
        env_file=str(env_file),
    )

    settings = get_settings()
    assert settings.llm_model_name == "MiniMax-M2.5"
    assert settings.get_llm_config()["api_key"] == "test-benchmark-key"


def test_load_runtime_env_removes_socks_proxy_when_socksio_missing(monkeypatch, tmp_path: Path):
    """加载 env 时，若未安装 socksio，应移除导致 httpx 失败的 SOCKS 代理。"""
    from scripts.runtime_env import load_runtime_env

    env_file = tmp_path / "runtime.env"
    env_file.write_text("LLM_PROVIDER=minimax\n", encoding="utf-8")

    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:7890")
    monkeypatch.setenv("HTTPS_PROXY", "socks5://127.0.0.1:7890")
    monkeypatch.setattr("scripts.runtime_env.importlib.util.find_spec", lambda name: None)

    load_runtime_env(str(env_file))

    assert "ALL_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ
