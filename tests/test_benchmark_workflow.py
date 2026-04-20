"""Benchmark profile 工作流节点回归测试。"""

from __future__ import annotations

from types import SimpleNamespace

from workflows.states import RunMetrics, SourceRecord, TaskItem, TopicSpec


class _FailIfCalledLLM:
    """若不应触发 LLM 调用时用于兜底。"""

    def invoke(self, messages):
        raise AssertionError("benchmark profile 不应调用该 LLM")


class _StaticLLM:
    """返回固定内容的测试 LLM。"""

    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):
        return SimpleNamespace(content=self._content)


def test_planner_node_uses_benchmark_tasks_without_llm(monkeypatch):
    """benchmark profile 下，Planner 应直接生成稳定任务。"""
    from agents import planner

    topic_spec = TopicSpec(
        id="T06C",
        topic="openclaw安装教程",
        expected_aspects=["安装前置条件 / 依赖", "编译或安装步骤", "常见错误与排查"],
        min_sources=4,
        min_words=2000,
    )
    monkeypatch.setattr(planner, "get_llm", lambda: _FailIfCalledLLM())

    result = planner.planner_node(
        {
            "research_topic": topic_spec.topic,
            "research_profile": "benchmark",
            "topic_spec": topic_spec,
        }
    )

    assert [task.expected_aspects for task in result["tasks"]] == [[aspect] for aspect in topic_spec.expected_aspects]
    assert all(task.task_type == "tutorial" for task in result["tasks"])


def test_researcher_node_selects_sources_and_tracks_rejections_for_benchmark(monkeypatch):
    """benchmark profile 下，Researcher 应只选中高相关来源并记录过滤统计。"""
    from agents import researcher

    task = TaskItem(
        id=1,
        title="依赖与前置条件",
        intent="重点覆盖方面：安装前置条件 / 依赖",
        query="openclaw安装教程 安装前置条件 / 依赖 installation requirements dependencies prerequisites",
        task_type="tutorial",
        expected_aspects=["安装前置条件 / 依赖"],
        preferred_sources=["web", "github"],
    )
    settings = SimpleNamespace(
        enabled_sources=["web", "github", "arxiv"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
    )
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: _StaticLLM("## 依赖与前置条件\n\n需要 SDL2 与资源文件。[1][2]"))
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "OpenClaw installation requirements",
                "url": "https://docs.example.com/openclaw/install",
                "snippet": "OpenClaw install requirements, SDL2 dependency and game assets.",
            },
            {
                "source_type": "web",
                "title": "OpenClaw AI Agent setup",
                "url": "https://ai.example.com/openclaw-agent",
                "snippet": "Personal AI assistant with chat memory and plugins.",
            },
        ],
    )
    monkeypatch.setattr(
        researcher,
        "search_github_repositories",
        lambda query, max_results=5: [
            {
                "source_type": "github",
                "title": "OpenClaw",
                "url": "https://github.com/opentomb/OpenClaw",
                "snippet": "Captain Claw open source engine with SDL2 build instructions.",
            }
        ],
    )
    monkeypatch.setattr(researcher, "search_arxiv_papers", lambda query, max_results=5: [])

    result = researcher.researcher_node(
        {
            "research_topic": "openclaw安装教程",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": [],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert len(result["sources_gathered"]) == 2
    assert all(source.selected for source in result["sources_gathered"])
    assert all(source.snapshot_ref for source in result["sources_gathered"])
    assert result["run_metrics"].selected_sources == 2
    assert result["run_metrics"].rejected_sources == 1
    assert result["evidence_notes"][0].selected_source_ids == [1, 2]


def test_researcher_node_benchmark_falls_back_to_deterministic_summary_when_llm_unavailable(monkeypatch):
    """benchmark profile 在 LLM 不可用时仍应生成可评测的稳定总结。"""
    from agents import researcher

    task = TaskItem(
        id=1,
        title="依赖与前置条件",
        intent="重点覆盖方面：安装前置条件 / 依赖",
        query="openclaw安装教程 安装前置条件 / 依赖 installation requirements dependencies prerequisites",
        task_type="tutorial",
        expected_aspects=["安装前置条件 / 依赖"],
        preferred_sources=["web", "github"],
    )
    settings = SimpleNamespace(
        enabled_sources=["web", "github"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
    )
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "OpenClaw installation requirements",
                "url": "https://docs.example.com/openclaw/install",
                "snippet": "OpenClaw install requirements, SDL2 dependency and game assets.",
            }
        ],
    )
    monkeypatch.setattr(
        researcher,
        "search_github_repositories",
        lambda query, max_results=5: [
            {
                "source_type": "github",
                "title": "OpenClaw",
                "url": "https://github.com/opentomb/OpenClaw",
                "snippet": "Captain Claw open source engine with SDL2 build instructions.",
            }
        ],
    )

    result = researcher.researcher_node(
        {
            "research_topic": "openclaw安装教程",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": [],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    summary = result["task_summaries"][0]
    assert "### 核心结论" in summary
    assert "### 补充观察" in summary
    assert "### 证据限制" in summary
    assert "[1]" in summary
    assert "[2]" in summary
    assert "安装前置条件 / 依赖" in summary


def test_researcher_node_records_capability_plan_and_skill_usage(tmp_path, monkeypatch):
    """Researcher 应暴露能力注册表，并记录任务级 capability plan。"""
    from agents import researcher

    skill_dir = tmp_path / "skills" / "install-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: install-guide
description: Improve installation and setup guidance.
---

Use this skill for installation, setup, requirements, and troubleshooting tasks.
""",
        encoding="utf-8",
    )

    task = TaskItem(
        id=1,
        title="安装步骤与配置",
        intent="重点覆盖方面：编译或安装步骤",
        query="openclaw安装教程 编译或安装步骤 installation guide setup",
        task_type="tutorial",
        expected_aspects=["编译或安装步骤"],
        preferred_sources=["web", "github"],
    )
    settings = SimpleNamespace(
        enabled_sources=["web", "github", "arxiv"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
        enabled_capability_types=["builtin", "skill"],
        skill_paths=[str(tmp_path / "skills")],
        mcp_servers=[],
        workspace_dir=str(tmp_path / "workspace"),
    )
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: _StaticLLM("## 安装步骤与配置\n\n先安装 SDL2，再构建项目。[1][2]"))
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "OpenClaw install guide",
                "url": "https://docs.example.com/openclaw/install",
                "snippet": "Install OpenClaw with SDL2 and game assets.",
            }
        ],
    )
    monkeypatch.setattr(
        researcher,
        "search_github_repositories",
        lambda query, max_results=5: [
            {
                "source_type": "github",
                "title": "OpenClaw repository",
                "url": "https://github.com/opentomb/OpenClaw",
                "snippet": "Open source engine build and install steps.",
            }
        ],
    )
    monkeypatch.setattr(researcher, "search_arxiv_papers", lambda query, max_results=5: [])

    result = researcher.researcher_node(
        {
            "research_topic": "openclaw安装教程",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": [],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [],
            "available_capabilities": [],
            "capability_plan": {},
            "tool_invocations": [],
            "run_metrics": RunMetrics(),
        }
    )

    capability_names = [cap.name for cap in result["available_capabilities"]]
    assert "skill.install-guide" in capability_names
    assert result["capability_plan"][task.title][0] == "skill.install-guide"
    assert result["run_metrics"].skill_activation_count == 1


def test_critic_node_keeps_failed_quality_gate_blocking_on_last_loop():
    """benchmark profile 到达最后一轮且 gate 失败时，不应再放行 Writer。"""
    from agents.critic import critic_node

    tasks = [
        TaskItem(
            id=1,
            title="定义与原理",
            intent="解释概念",
            query="RAG 基本原理",
            expected_aspects=["RAG 基本原理（检索 + 生成）"],
            task_type="research",
        ),
        TaskItem(
            id=2,
            title="评估指标",
            intent="解释评估",
            query="RAG Faithfulness Relevance Recall",
            expected_aspects=["评估指标（Faithfulness / Relevance / Recall）"],
            task_type="research",
        ),
    ]
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="web",
            query="RAG 基本原理",
            title="RAG guide",
            trust_tier=4,
            selected=True,
        )
    ]

    result = critic_node(
        {
            "research_topic": "RAG（检索增强生成）技术的原理和应用",
            "research_profile": "benchmark",
            "tasks": tasks,
            "task_summaries": ["## 定义与原理\n\nRAG 结合检索与生成。[1]", "## 评估指标\n\n这里没有涉及 Recall。"],
            "sources_gathered": sources,
            "loop_count": 1,
            "max_loops": 2,
            "run_metrics": RunMetrics(),
        }
    )

    assert result["quality_gate_status"] == "failed"
    assert result["critic_feedback"].is_sufficient is False
    assert result["critic_feedback"].follow_up_queries


def test_graph_routes_failed_quality_gate_to_terminal_failure():
    """严格 gate 失败时，工作流应进入失败终态，而不是继续写报告。"""
    from workflows.graph import _should_continue
    from workflows.states import CriticFeedback

    route = _should_continue(
        {
            "quality_gate_status": "failed",
            "critic_feedback": CriticFeedback(
                quality_score=6,
                is_sufficient=False,
                gaps=["行业应用案例"],
                follow_up_queries=["agent case study official deployment"],
                feedback="缺少真实案例证据。",
            ),
        }
    )

    assert route == "fail_quality_gate"


def test_writer_node_uses_benchmark_report_builder_without_llm(monkeypatch):
    """benchmark profile 下，Writer 应走确定性报告生成。"""
    from agents import writer
    from evaluation.metrics import citation_accuracy

    monkeypatch.setattr(writer, "get_llm", lambda: _FailIfCalledLLM())
    sources = [
        SourceRecord(citation_id=1, source_type="github", query="q", title="Used source", url="https://used.example.com", selected=True, trust_tier=5),
        SourceRecord(citation_id=2, source_type="web", query="q", title="Unused source", url="https://unused.example.com", selected=False, trust_tier=2),
    ]
    task = TaskItem(
        id=1,
        title="定义与原理",
        intent="解释概念",
        query="RAG 基本原理",
        expected_aspects=["RAG 基本原理（检索 + 生成）"],
        task_type="research",
    )
    evidence_note = {
        "task_id": 1,
        "task_title": "定义与原理",
        "query": "RAG 基本原理",
        "summary": "### 核心结论\n\nRAG 结合检索与生成。[1]",
        "source_ids": [1],
        "selected_source_ids": [1],
    }

    result = writer.writer_node(
        {
            "research_topic": "RAG（检索增强生成）技术的原理和应用",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": ["### 核心结论\n\nRAG 结合检索与生成。[1]\n\n### 证据限制\n\n当前证据仍有限。"],
            "sources_gathered": sources,
            "evidence_notes": [evidence_note],
            "run_metrics": RunMetrics(),
        }
    )

    assert "## 参考来源" in result["final_report"]
    assert "### 核心结论" in result["final_report"]
    assert "Used source" in result["final_report"]
    assert "Unused source" not in result["final_report"]
    assert citation_accuracy(result["final_report"]) == 1.0
    assert "## 概述" in result["final_report"]
    assert "## 总结" in result["final_report"]


def test_researcher_uses_llm_summary_in_benchmark_when_available(monkeypatch):
    """benchmark profile 下若 LLM 可用，应优先使用 LLM 总结，而不是总是 deterministic 回退。"""
    from agents import researcher

    class _FakeResponse:
        content = (
            "### 核心结论\n\n"
            "RAG 基本原理（检索 + 生成）可以概括为：模型先检索相关资料，再利用检索结果生成回答。[1]\n\n"
            "### 证据限制\n\n"
            "当前仍需更多证据。[1]"
        )

    class _FakeLLM:
        def invoke(self, messages):
            return _FakeResponse()

    task = TaskItem(
        id=1,
        title="定义与原理",
        intent="解释概念",
        query="RAG 基本原理",
        expected_aspects=["RAG 基本原理（检索 + 生成）"],
        task_type="research",
    )
    settings = SimpleNamespace(
        enabled_sources=["web"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
        workspace_dir="workspace",
        mcp_config_path=None,
        mcp_servers=[],
    )
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: _FakeLLM())
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "RAG guide",
                "url": "https://docs.example.com/rag",
                "snippet": "RAG combines retrieval and generation for grounded responses.",
            }
        ],
    )
    monkeypatch.setattr(researcher, "search_github_repositories", lambda query, max_results=5: [])
    monkeypatch.setattr(researcher, "search_arxiv_papers", lambda query, max_results=5: [])

    result = researcher.researcher_node(
        {
            "research_topic": "RAG（检索增强生成）技术的原理和应用",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": [],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    assert result["task_summaries"]
    assert "模型先检索相关资料" in result["task_summaries"][0]


def test_researcher_follow_up_queries_replace_original_task_summary(monkeypatch):
    """补检索命中某个 task 时，应回填原任务而不是追加一条补充研究。"""
    from agents import researcher

    task = TaskItem(
        id=1,
        title="安装步骤与配置",
        intent="重点覆盖方面：编译或安装步骤",
        query="openclaw安装教程 编译或安装步骤 install tutorial setup guide",
        task_type="tutorial",
        expected_aspects=["编译或安装步骤"],
        preferred_sources=["web", "github"],
    )
    settings = SimpleNamespace(
        enabled_sources=["web", "github"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
    )
    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: (_ for _ in ()).throw(RuntimeError("missing llm")))
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "OpenClaw install guide",
                "url": "https://docs.example.com/openclaw/install",
                "snippet": "OpenClaw install tutorial with setup steps and quick start.",
            }
        ],
    )
    monkeypatch.setattr(researcher, "search_github_repositories", lambda query, max_results=5: [])

    result = researcher.researcher_node(
        {
            "research_topic": "openclaw安装教程",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": ["## 安装步骤与配置\n\n暂无可用信息。"],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [
                {
                    "task_id": 1,
                    "task_title": "安装步骤与配置",
                    "query": task.query,
                    "summary": "## 安装步骤与配置\n\n暂无可用信息。",
                    "source_ids": [],
                    "selected_source_ids": [],
                }
            ],
            "critic_feedback": SimpleNamespace(follow_up_queries=["openclaw安装教程 编译或安装步骤 official documentation github install troubleshooting"]),
            "run_metrics": RunMetrics(),
        }
    )

    assert len(result["task_summaries"]) == 1
    assert "本节直接覆盖方面：编译或安装步骤" in result["task_summaries"][0]


def test_researcher_repairs_invalid_benchmark_summary_with_deterministic_fallback(monkeypatch):
    """benchmark profile 下，LLM 总结若缺方面/缺引用，应触发 deterministic repair。"""
    from agents import researcher

    task = TaskItem(
        id=1,
        title="行业应用案例",
        intent="重点覆盖方面：行业应用案例",
        query="AI Agent 行业应用案例 official case study customer story deployment production use",
        task_type="product",
        expected_aspects=["行业应用案例"],
        preferred_sources=["web", "github"],
    )
    settings = SimpleNamespace(
        enabled_sources=["web", "github"],
        max_search_results=5,
        per_source_max_results=4,
        per_task_selected_sources=4,
    )

    monkeypatch.setattr(researcher, "get_settings", lambda: settings)
    monkeypatch.setattr(researcher, "get_llm", lambda: _StaticLLM("### 核心结论\n\n这里是泛化背景介绍，没有引用。"))
    monkeypatch.setattr(
        researcher,
        "search_web",
        lambda query, max_results=5: [
            {
                "source_type": "web",
                "title": "OpenAI customer story",
                "url": "https://openai.com/customer-stories/agent-deployment",
                "snippet": "Official customer story about deploying AI agents in production.",
            }
        ],
    )
    monkeypatch.setattr(
        researcher,
        "search_github_repositories",
        lambda query, max_results=5: [
            {
                "source_type": "github",
                "title": "openai/agents-examples",
                "url": "https://github.com/openai/agents-examples",
                "snippet": "Official examples and reference architectures for production agent systems.",
                "owner": "openai",
            }
        ],
    )
    monkeypatch.setattr(researcher, "search_arxiv_papers", lambda query, max_results=5: [])

    result = researcher.researcher_node(
        {
            "research_topic": "AI Agent 行业应用案例",
            "research_profile": "benchmark",
            "tasks": [task],
            "task_summaries": [],
            "sources_gathered": [],
            "search_results": [],
            "evidence_notes": [],
            "run_metrics": RunMetrics(),
        }
    )

    summary = result["task_summaries"][0]
    assert "### 核心结论" in summary
    assert "行业应用案例" in summary
    assert "[1]" in summary or "[2]" in summary
    assert result["run_metrics"].summary_repair_count == 1
    assert result["run_metrics"].summary_repair_tasks == ["行业应用案例"]
