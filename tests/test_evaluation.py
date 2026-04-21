"""评估与 runner 回归测试。"""

from __future__ import annotations

from types import SimpleNamespace

from configs.settings import Settings
from legacy.workflows.states import SourceRecord


class _FakeLLM:
    """可注入固定响应的 LLM 假对象。"""

    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):
        return SimpleNamespace(content=self._content)


def test_pairwise_judge_maps_x_y_back_to_a_b():
    """pairwise 盲评结果应映射回 A/B 标签。"""
    from evaluation.llm_judge import LLMJudge

    judge = LLMJudge(
        llm=_FakeLLM(
            """
            {
              "report_x": {"overall": 8.1},
              "report_y": {"overall": 7.4},
              "winner": "X",
              "reason": "X 更好"
            }
            """
        )
    )

    result = judge.compare_reports("短报告 A", "更长一些的报告 B", topic="测试主题")

    assert result["winner"] == "A"
    assert result["report_a"]["overall"] == 8.1
    assert result["report_b"]["overall"] == 7.4


def test_evaluate_report_prefers_structured_sources_and_aspects():
    """综合评估应优先使用结构化来源与方面覆盖。"""
    from evaluation.metrics import evaluate_report

    report = "# 报告\n\n性能分析 [1]\n\n成本分析 [2]"
    sources = [
        SourceRecord(citation_id=1, source_type="web", query="性能", title="来源 1"),
        SourceRecord(citation_id=2, source_type="github", query="成本", title="来源 2"),
        SourceRecord(citation_id=3, source_type="arxiv", query="背景", title="来源 3"),
    ]

    metrics = evaluate_report(
        report,
        source_records=sources,
        expected_aspects=["性能", "成本"],
    )

    assert metrics["source_coverage"] == 3
    assert metrics["aspect_coverage"] == 1.0


def test_gptr_runner_builds_environment_from_existing_env(monkeypatch):
    """GPT Researcher runner 不应注入硬编码密钥。"""
    from scripts.run_gptr_isolated import build_runner_environment

    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "env-tavily-key")

    env = build_runner_environment({"EXTRA": "1"})

    assert env["OPENAI_API_KEY"] == "env-openai-key"
    assert env["TAVILY_API_KEY"] == "env-tavily-key"
    assert env["EXTRA"] == "1"


def test_llm_judge_uses_explicit_judge_model(monkeypatch):
    """显式配置 judge_model 时，Judge 应使用独立模型。"""
    from evaluation import llm_judge

    captured = {}
    settings = Settings(llm_model_name="main-model", judge_model="judge-model")

    def fake_get_llm(resolved_settings):
        captured["model"] = resolved_settings.llm_model_name
        return _FakeLLM("{}")

    monkeypatch.setattr(llm_judge, "get_settings", lambda: settings)
    monkeypatch.setattr(llm_judge, "get_llm", fake_get_llm)

    judge = llm_judge.LLMJudge()
    _ = judge.llm

    assert captured["model"] == "judge-model"


def test_llm_judge_follows_primary_model_without_override(monkeypatch):
    """未配置 judge_model 时，Judge 应沿用主模型。"""
    from evaluation import llm_judge

    captured = {}
    settings = Settings(llm_model_name="main-model", judge_model=None)

    def fake_get_llm(resolved_settings):
        captured["model"] = resolved_settings.llm_model_name
        return _FakeLLM("{}")

    monkeypatch.setattr(llm_judge, "get_settings", lambda: settings)
    monkeypatch.setattr(llm_judge, "get_llm", fake_get_llm)

    judge = llm_judge.LLMJudge()
    _ = judge.llm

    assert captured["model"] == "main-model"
