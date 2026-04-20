"""基础单元测试——验证核心模块的导入和基本功能。

运行方式：
    uv run python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfigSettings:
    """测试配置管理模块。"""

    def test_settings_import(self):
        """验证 Settings 类可以正常导入。"""
        from configs.settings import Settings
        assert Settings is not None

    def test_settings_defaults(self):
        """验证默认配置值正确。"""
        from configs.settings import Settings, LLMProvider, SearchBackend

        s = Settings()
        assert s.llm_provider == LLMProvider.MINIMAX
        assert s.search_backend == SearchBackend.TAVILY
        assert s.max_research_loops == 3
        assert s.max_search_results == 5
        assert s.bundle_emission_enabled is True
        assert s.bundle_output_dirname == "bundles"
        assert s.job_runtime_dirname == "research_jobs"
        assert s.job_heartbeat_interval_seconds == 2
        assert s.job_stale_timeout_seconds == 15
        assert s.legacy_cli_enabled is True
        assert s.connector_substrate_enabled is True
        assert s.snapshot_store_dirname == "snapshots"
        assert s.source_policy_mode == "open-web"

    def test_get_llm_config(self):
        """验证 LLM 配置字典生成。"""
        from configs.settings import Settings

        s = Settings()
        config = s.get_llm_config()
        assert "model" in config
        assert "base_url" in config
        assert "temperature" in config


class TestLLMClean:
    """测试 LLM 输出清洗模块。"""

    def test_clean_think_tags(self):
        """验证 <think> 标签清理。"""
        from llm.clean import clean_llm_output

        text = "<think>\n这是思维链\n</think>\n\n# 标题\n正文内容"
        result = clean_llm_output(text)
        assert "<think>" not in result
        assert "# 标题" in result
        assert "正文内容" in result

    def test_clean_empty_input(self):
        """验证空输入处理。"""
        from llm.clean import clean_llm_output

        assert clean_llm_output("") == ""
        assert clean_llm_output("   ") == ""

    def test_extract_json(self):
        """验证 JSON 提取。"""
        from llm.clean import extract_json_from_output

        text = '<think>思考中</think>\n```json\n{"key": "value"}\n```'
        result = extract_json_from_output(text)
        parsed = json.loads(result)
        assert parsed["key"] == "value"


class TestEvaluationMetrics:
    """测试评估指标模块。"""

    def test_citation_accuracy(self):
        """验证引用准确率计算。"""
        from evaluation.metrics import citation_accuracy

        report = "这是第一段 [1]。\n\n这是第二段 [2]。\n\n这是无引用段。"
        score = citation_accuracy(report)
        assert 0 <= score <= 1
        assert score > 0  # 至少部分段落有引用

    def test_source_coverage(self):
        """验证来源覆盖率计算。"""
        from evaluation.metrics import source_coverage

        report = "引用 [1] 和 [2] 和 [3]。另外 [1] 再次出现。"
        count = source_coverage(report)
        assert count == 3  # 唯一引用编号：1, 2, 3

    def test_report_depth(self):
        """验证报告深度评估。"""
        from evaluation.metrics import report_depth

        report = "# 标题\n\n## 第一章\n\n段落1\n\n## 第二章\n\n段落2"
        result = report_depth(report)
        assert result["heading_count"] >= 2
        assert result["word_count"] > 0

    def test_evaluate_report(self):
        """验证综合评估。"""
        from evaluation.metrics import evaluate_report

        report = "# 报告\n\n内容 [1]\n\n## 章节\n\n更多内容 [2]"
        result = evaluate_report(report)
        assert "citation_accuracy" in result
        assert "source_coverage" in result
        assert "depth_score" in result


class TestWorkflowStates:
    """测试工作流状态模型。"""

    def test_task_item(self):
        """验证 TaskItem 创建。"""
        from workflows.states import TaskItem

        task = TaskItem(id=1, title="测试", intent="验证", query="test query")
        assert task.status == "pending"
        assert task.summary is None

    def test_critic_feedback(self):
        """验证 CriticFeedback 创建。"""
        from workflows.states import CriticFeedback

        fb = CriticFeedback(quality_score=8, is_sufficient=True, feedback="好")
        assert fb.quality_score == 8
        assert fb.is_sufficient is True

    def test_graph_build(self):
        """验证 LangGraph 工作流可以构建。"""
        from workflows.graph import build_research_graph

        graph = build_research_graph()
        assert graph is not None


class TestMemoryStore:
    """测试 Memory 存储模块。"""

    def test_memory_init(self, tmp_path):
        """验证 MemoryStore 目录初始化。"""
        from memory.store import MemoryStore

        store = MemoryStore(workspace_dir=str(tmp_path / "test_workspace"))
        assert store.notes_dir.exists()
        assert store.sources_dir.exists()
        assert store.summaries_dir.exists()

    def test_save_note(self, tmp_path):
        """验证笔记保存。"""
        from memory.store import MemoryStore

        store = MemoryStore(workspace_dir=str(tmp_path / "test_workspace"))
        path = store.save_note("测试笔记", "这是内容", "测试主题")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "测试笔记" in content
        assert "这是内容" in content
