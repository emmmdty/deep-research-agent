"""Benchmark profile 与研究策略回归测试。"""

from __future__ import annotations

from workflows.states import EvidenceNote, SourceRecord, TaskItem, TopicSpec


def test_build_benchmark_tasks_covers_all_expected_aspects():
    """benchmark profile 应按 expected_aspects 生成稳定任务。"""
    from research_policy import build_benchmark_tasks

    topic = TopicSpec(
        id="T02",
        topic="RAG（检索增强生成）技术的原理和应用",
        expected_aspects=[
            "RAG 基本原理（检索 + 生成）",
            "Naive RAG vs Advanced RAG vs Modular RAG",
            "向量数据库选型（FAISS / Milvus / Chroma）",
            "Chunking 策略和 Embedding 模型选择",
            "评估指标（Faithfulness / Relevance / Recall）",
        ],
        min_sources=5,
        min_words=3000,
    )

    tasks = build_benchmark_tasks(topic)

    assert len(tasks) == 5
    assert [task.expected_aspects for task in tasks] == [[aspect] for aspect in topic.expected_aspects]
    assert all(task.task_type == "research" for task in tasks)


def test_tutorial_tasks_include_bilingual_required_terms():
    """教程类任务的 must_include_terms 应包含中英混合关键词，避免英文文档被误杀。"""
    from research_policy import build_benchmark_tasks

    topic = TopicSpec(
        id="T06C",
        topic="openclaw安装教程",
        expected_aspects=["编译或安装步骤"],
        min_sources=4,
        min_words=2000,
    )

    task = build_benchmark_tasks(topic)[0]

    assert "install" in task.must_include_terms
    assert "setup" in task.must_include_terms


def test_infer_task_type_and_source_policy_for_tutorial_topics():
    """教程类主题应优先使用 web + github，禁用 arxiv。"""
    from research_policy import infer_task_type, preferred_sources_for_task, should_use_source

    task_type = infer_task_type("openclaw安装教程")

    assert task_type == "tutorial"
    assert preferred_sources_for_task(task_type) == ["web", "github"]
    assert should_use_source(task_type, "arxiv") is False


def test_select_sources_for_task_rejects_off_topic_and_duplicates():
    """来源筛选应保留与锚点一致的结果，并过滤重复/偏题结果。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T06C",
        topic="openclaw安装教程",
        expected_aspects=["安装前置条件 / 依赖"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]
    raw_items = [
        {
            "source_type": "github",
            "title": "OpenClaw Engine",
            "url": "https://github.com/opentomb/OpenClaw",
            "snippet": "Captain Claw game engine source code and assets loader",
        },
        {
            "source_type": "web",
            "title": "OpenClaw installation requirements",
            "url": "https://docs.example.com/openclaw/install",
            "snippet": "OpenClaw game engine install requirements, SDL dependencies, CLAW.REZ setup",
        },
        {
            "source_type": "web",
            "title": "OpenClaw installation requirements",
            "url": "https://docs.example.com/openclaw/install",
            "snippet": "duplicate result should be removed",
        },
        {
            "source_type": "web",
            "title": "OpenClaw AI Agent setup",
            "url": "https://ai.example.com/openclaw-agent",
            "snippet": "personal AI assistant with Node.js and chat apps",
        },
    ]

    selected, rejected, stats = select_sources_for_task(raw_items, task, per_task_limit=4)

    assert [item["title"] for item in selected] == [
        "OpenClaw Engine",
        "OpenClaw installation requirements",
    ]
    assert len(rejected) == 2
    assert stats["off_topic_reject_count"] == 1
    assert stats["duplicate_reject_count"] == 1


def test_evaluate_quality_gate_requires_aspect_coverage_and_sources():
    """质量门控应在方面覆盖缺失时拒绝通过，并生成定向补检索。"""
    from research_policy import evaluate_quality_gate

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
    summaries = [
        "## 定义与原理\n\nRAG 结合检索与生成来降低幻觉。[1]",
        "## 评估指标\n\n这里没有涉及 Faithfulness 或 Recall。",
    ]
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="web",
            query="RAG 基本原理",
            title="RAG guide",
            trust_tier=4,
            selected=True,
        ),
        SourceRecord(
            citation_id=2,
            source_type="web",
            query="RAG Faithfulness Relevance Recall",
            title="RAG metrics overview",
            trust_tier=3,
            selected=True,
        ),
    ]

    gate = evaluate_quality_gate(
        tasks=tasks,
        task_summaries=summaries,
        sources=sources,
        loop_count=0,
        max_loops=2,
    )

    assert gate["passed"] is False
    assert gate["quality_gate_status"] == "needs_more_research"
    assert gate["missing_aspects"] == ["评估指标（Faithfulness / Relevance / Recall）"]
    assert gate["follow_up_queries"] == ["RAG（检索增强生成）技术的原理和应用 评估指标 Faithfulness Relevance Recall"] or gate["follow_up_queries"]


def test_evaluate_quality_gate_generates_official_first_follow_up_queries():
    """缺失方面时，应生成更强的官方优先补检索查询。"""
    from research_policy import evaluate_quality_gate

    tasks = [
        TaskItem(
            id=1,
            title="行业应用案例",
            intent="重点覆盖方面：行业应用案例",
            query="2024年大语言模型Agent架构的最新进展 行业应用案例",
            expected_aspects=["行业应用案例"],
            task_type="product",
        )
    ]
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="web",
            query="2024年大语言模型Agent架构的最新进展 行业应用案例",
            title="博客文章",
            trust_tier=3,
            selected=True,
        )
    ]

    gate = evaluate_quality_gate(
        tasks=tasks,
        task_summaries=["## 行业应用案例\n\n这里只讨论了背景，没有给出案例。"],
        sources=sources,
        loop_count=0,
        max_loops=3,
        research_topic="2024年大语言模型Agent架构的最新进展",
    )

    assert gate["passed"] is False
    assert gate["follow_up_queries"]
    assert any("official" in query.lower() or "github" in query.lower() for query in gate["follow_up_queries"])


def test_select_sources_for_task_keeps_high_trust_mix_for_research_topics():
    """研究类主题应尽量保留高可信 github/arxiv 结果，避免被普通 web 结果挤掉。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["Memory 和长期记忆机制"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]
    raw_items = [
        {
            "source_type": "web",
            "title": "Blog about agent memory",
            "url": "https://blog.example.com/agent-memory",
            "snippet": "A broad blog post about memory, storage, and apps.",
        },
        {
            "source_type": "github",
            "title": "langchain-ai/langgraph",
            "url": "https://github.com/langchain-ai/langgraph",
            "snippet": "Build stateful, multi-actor applications with LLMs and memory.",
        },
        {
            "source_type": "arxiv",
            "title": "A Survey on Memory for LLM Agents",
            "url": "https://arxiv.org/abs/2401.00001",
            "snippet": "Survey of episodic, semantic, and long-term memory for LLM agents.",
        },
        {
            "source_type": "web",
            "title": "Another blog about memory",
            "url": "https://notes.example.com/memory",
            "snippet": "Memory notes and community discussion.",
        },
    ]

    selected, rejected, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 3
    assert any(item["source_type"] == "github" for item in selected)
    assert any(item["source_type"] == "arxiv" for item in selected)


def test_build_benchmark_report_keeps_only_used_references():
    """benchmark writer 应只保留正文实际引用过的来源。"""
    from research_policy import build_benchmark_report
    from evaluation.metrics import citation_accuracy

    tasks = [
        TaskItem(
            id=1,
            title="定义与原理",
            intent="解释概念",
            query="RAG 基本原理",
            expected_aspects=["RAG 基本原理（检索 + 生成）"],
            task_type="research",
        )
    ]
    summaries = ["### 核心结论\n\nRAG 结合检索与生成。[1]\n\n### 证据限制\n\n当前结论仍需更多论文验证。"]
    sources = [
        SourceRecord(citation_id=1, source_type="github", query="q", title="Used source", url="https://used.example.com", selected=True, trust_tier=5),
        SourceRecord(citation_id=2, source_type="web", query="q", title="Unused source", url="https://unused.example.com", selected=True),
    ]
    evidence_notes = [
        EvidenceNote(
            task_id=1,
            task_title="定义与原理",
            query="RAG 基本原理",
            summary=summaries[0],
            source_ids=[1],
            selected_source_ids=[1],
        )
    ]

    report = build_benchmark_report(
        topic="RAG（检索增强生成）技术的原理和应用",
        tasks=tasks,
        task_summaries=summaries,
        sources=sources,
        evidence_notes=evidence_notes,
    )

    assert "[1] Used source - https://used.example.com" in report
    assert "Unused source" not in report
    assert citation_accuracy(report) == 1.0
    assert "## 概述" in report and "[1]" in report.split("## 1.")[0]
    assert "## 总结" in report and "[1]" in report.split("## 参考来源")[0]
