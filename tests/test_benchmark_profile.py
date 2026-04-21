"""Benchmark profile 与研究策略回归测试。"""

from __future__ import annotations

from legacy.workflows.states import EvidenceNote, SourceRecord, TaskItem, TopicSpec


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

    assert {item["title"] for item in selected} == {
        "OpenClaw Engine",
        "OpenClaw installation requirements",
    }
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


def test_case_study_tasks_prefer_web_and_github_with_official_queries():
    """真实案例类方面应优先 web/github，并使用官方案例导向查询。"""
    from research_policy import build_benchmark_tasks, build_source_query

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["行业应用案例"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    assert task.task_type == "product"
    assert task.preferred_sources == ["web", "github"]

    web_query = build_source_query(task, "web").lower()
    github_query = build_source_query(task, "github").lower()
    arxiv_query = build_source_query(task, "arxiv").lower()

    assert "official" in web_query
    assert "case study" in web_query
    assert any(marker in web_query for marker in ("customer story", "deployment", "production use"))
    assert any(marker in github_query for marker in ("application", "production", "example", "project"))
    assert "paper" not in arxiv_query
    assert "survey" not in arxiv_query


def test_case_study_query_bundle_prefers_official_domains_and_repo_search():
    """case-study 任务应生成官方域名优先的 query bundle，而不是只用单条泛查询。"""
    from research_policy import build_benchmark_tasks, build_source_queries

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["行业应用案例"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    web_queries = build_source_queries(task, "web")
    github_queries = build_source_queries(task, "github")

    assert len(web_queries) >= 3
    assert any("site:openai.com" in query for query in web_queries)
    assert any("site:anthropic.com" in query for query in web_queries)
    assert any("customer story" in query.lower() or "case study" in query.lower() for query in web_queries)
    assert len(github_queries) >= 2
    assert any("org:openai" in query.lower() or "org:langchain-ai" in query.lower() for query in github_queries)
    assert any("example" in query.lower() or "project" in query.lower() for query in github_queries)


def test_finance_case_study_query_bundle_is_topic_aware():
    """金融类 case-study 应优先使用金融/云厂商官方域名与金融 family terms。"""
    from research_policy import build_benchmark_tasks, build_source_queries

    topic = TopicSpec(
        id="T04",
        topic="AI Agent 在金融领域的应用案例",
        expected_aspects=["智能投顾和量化交易", "风控和反欺诈", "客户服务自动化"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    web_queries = build_source_queries(task, "web")

    assert any("site:aws.amazon.com" in query for query in web_queries)
    assert any("site:microsoft.com" in query or "site:learn.microsoft.com" in query for query in web_queries)
    assert any("financial services" in query.lower() or "banking" in query.lower() for query in web_queries)
    assert any("robo advisor" in query.lower() or "quantitative trading" in query.lower() for query in web_queries)


def test_select_sources_for_case_study_rejects_survey_like_evidence():
    """行业案例方面只接受真实落地案例证据，survey/review/benchmark 不应通过。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["行业应用案例"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    raw_items = [
        {
            "source_type": "web",
            "title": "OpenAI customer story - agent deployment",
            "url": "https://openai.com/index/outtake",
            "snippet": "Official customer story describing production deployment of an agent workflow.",
        },
        {
            "source_type": "web",
            "title": "Survey of LLM agents in industry",
            "url": "https://blog.example.com/agent-survey",
            "snippet": "A broad survey and benchmark overview of agent systems and enterprise trends.",
        },
        {
            "source_type": "github",
            "title": "openai/openai-agents-examples",
            "url": "https://github.com/openai/openai-agents-examples",
            "snippet": "Production application example for a multi-agent workflow in customer support.",
        },
    ]

    selected, rejected, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 2
    assert all(item.get("rejection_reason") != "not_case_study_evidence" for item in selected)
    assert any(item.get("rejection_reason") == "not_case_study_evidence" for item in rejected)


def test_select_sources_for_case_study_marks_official_and_first_party_strength():
    """case-study 来源应写入结构化类型、强度分和主题贴合标记。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["行业应用案例"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    raw_items = [
        {
            "source_type": "web",
            "title": "Outtake's agents resolve cybersecurity attacks in hours with OpenAI",
            "url": "https://openai.com/index/outtake",
            "snippet": "Customer story showing agents in production with measurable outcomes and function calling.",
        },
        {
            "source_type": "github",
            "title": "openai/openai-agents-examples",
            "url": "https://github.com/openai/openai-agents-examples",
            "snippet": "Official examples and production-ready agent projects maintained by OpenAI.",
        },
    ]

    selected, _, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 2
    official = next(item for item in selected if item["source_type"] == "web")
    repo = next(item for item in selected if item["source_type"] == "github")
    assert official["case_study_type"] == "official_customer_story"
    assert official["matches_topic_family"] is True
    assert official["case_study_strength_score"] >= 0.8
    assert repo["case_study_type"] == "first_party_repo"
    assert repo["case_study_strength_score"] >= 0.65


def test_finance_case_study_accepts_official_english_compliance_evidence():
    """金融案例应接受英文官方合规案例，不要求逐字命中中文方面短语。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T04",
        topic="AI Agent 在金融领域的应用案例",
        expected_aspects=["监管合规检查"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    raw_items = [
        {
            "source_type": "web",
            "title": "AWS customer story: financial services compliance automation",
            "url": "https://aws.amazon.com/financial-services/customer-stories/compliance-automation/",
            "snippet": "Official customer story showing production deployment for banking compliance, AML and KYC workflows with measurable efficiency gains.",
        },
        {
            "source_type": "web",
            "title": "Finance AI overview",
            "url": "https://blog.example.com/finance-ai-overview",
            "snippet": "A broad overview of AI trends in finance without customer deployment details.",
        },
    ]

    selected, rejected, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 1
    official = selected[0]
    assert official["case_study_type"] == "official_customer_story"
    assert official["matches_topic_family"] is True
    assert official["case_study_strength_score"] >= 0.9
    assert official["support_specificity"] >= 0.7
    assert any(item.get("rejection_reason") == "not_case_study_evidence" for item in rejected)


def test_mcp_official_docs_are_not_rejected_as_weak_support_for_generic_aspects():
    """MCP 主题下的通用方面应把 MCP/tool discovery/security 词汇纳入支撑判定。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T11",
        topic="使用 MCP 为研究型 Agent 接入外部工具的最佳实践",
        expected_aspects=["权限与安全"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    raw_items = [
        {
            "source_type": "web",
            "title": "Model context protocol (MCP) - OpenAI Agents SDK",
            "url": "https://openai.github.io/openai-agents-python/mcp/",
            "snippet": "Official documentation covering MCP tool discovery, server integration, permission boundaries, authorization, and access control patterns.",
        }
    ]

    selected, rejected, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 1
    assert selected[0]["support_specificity"] >= 0.3
    assert not rejected


def test_mcp_integration_pattern_accepts_transport_specific_docs():
    """MCP 实际接入模式应识别 stdio/SSE/streamable-http 这类运输层接法。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T11",
        topic="使用 MCP 为研究型 Agent 接入外部工具的最佳实践",
        expected_aspects=["实际接入模式"],
        min_sources=4,
        min_words=2000,
    )
    task = build_benchmark_tasks(topic)[0]

    raw_items = [
        {
            "source_type": "web",
            "title": "Model context protocol (MCP) - OpenAI Agents SDK",
            "url": "https://openai.github.io/openai-agents-python/mcp/",
            "snippet": "Official documentation covering MCP integration patterns, stdio transport, SSE connections, streamable HTTP, and tool integration design.",
        }
    ]

    selected, rejected, _ = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert len(selected) == 1
    assert selected[0]["support_specificity"] >= 0.3
    assert not rejected


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

    assert len(selected) == 2
    assert any(item["source_type"] == "github" for item in selected)
    assert any(item["source_type"] == "arxiv" for item in selected)
    assert all(item["source_type"] in {"github", "arxiv"} for item in selected)


def test_select_sources_for_task_rejects_withdrawn_and_topic_guard_miss():
    """现代 LLM 主题下，撤稿/明显偏题的高可信来源也必须被拒绝。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["ReAct / Plan-and-Execute / Multi-Agent 等主流架构"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]
    raw_items = [
        {
            "source_type": "arxiv",
            "title": "This paper has been withdrawn",
            "url": "https://arxiv.org/abs/cond-mat/0309395",
            "snippet": "This paper has been withdrawn",
            "published_at": "2003-09-17",
        },
        {
            "source_type": "arxiv",
            "title": "A Survey of Multi-Agent Deep Reinforcement Learning with Communication",
            "url": "https://arxiv.org/abs/2203.08975",
            "snippet": "Survey of multi-agent reinforcement learning with communication.",
            "published_at": "2022-03-16",
        },
        {
            "source_type": "arxiv",
            "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
            "url": "https://arxiv.org/abs/2210.03629",
            "snippet": "ReAct prompts language models to generate reasoning traces and task-specific actions.",
            "published_at": "2022-10-07",
        },
    ]

    selected, rejected, stats = select_sources_for_task(raw_items, task, per_task_limit=3)

    assert [item["title"] for item in selected] == [
        "ReAct: Synergizing Reasoning and Acting in Language Models"
    ]
    assert {item["rejection_reason"] for item in rejected} == {"withdrawn", "domain_conflict"}
    assert stats["off_topic_reject_count"] == 2


def test_build_source_query_uses_topic_aliases_for_research_sources():
    """研究类 github/arxiv 查询应注入英文别名，但避免把平台噪声词塞进检索语句。"""
    from research_policy import build_benchmark_tasks, build_source_query

    topic = TopicSpec(
        id="T02",
        topic="RAG（检索增强生成）技术的原理和应用",
        expected_aspects=["评估指标（Faithfulness / Relevance / Recall）"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]

    github_query = build_source_query(task, "github")
    arxiv_query = build_source_query(task, "arxiv")

    assert "RAG" in github_query or "retrieval augmented generation" in github_query.lower()
    assert "github" not in github_query.lower()
    assert "readme" not in github_query.lower()
    assert "paper" in arxiv_query.lower()
    assert "survey" in arxiv_query.lower()
    assert "faithfulness" in arxiv_query.lower()


def test_build_benchmark_tasks_prefers_practical_sources_for_concrete_stack_aspects():
    """具体技术栈方面应优先走 web/github，避免泛 arXiv 结果主导。"""
    from research_policy import build_benchmark_tasks

    topic = TopicSpec(
        id="T02",
        topic="RAG（检索增强生成）技术的原理和应用",
        expected_aspects=["向量数据库选型（FAISS / Milvus / Chroma）"],
        min_sources=5,
        min_words=3000,
    )

    task = build_benchmark_tasks(topic)[0]

    assert task.preferred_sources == ["web", "github"]


def test_build_benchmark_tasks_prefers_academic_sources_for_architecture_aspects():
    """抽象架构类方面应优先走 web/arxiv，避免随机 GitHub repo 污染结论。"""
    from research_policy import build_benchmark_tasks

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["ReAct / Plan-and-Execute / Multi-Agent 等主流架构"],
        min_sources=5,
        min_words=3000,
    )

    task = build_benchmark_tasks(topic)[0]

    assert task.preferred_sources == ["web", "arxiv"]


def test_select_sources_for_task_rejects_generic_rag_papers_for_vector_db_aspect():
    """具体组件方面不应再把泛 RAG 论文当成直接证据。"""
    from research_policy import build_benchmark_tasks, select_sources_for_task

    topic = TopicSpec(
        id="T02",
        topic="RAG（检索增强生成）技术的原理和应用",
        expected_aspects=["向量数据库选型（FAISS / Milvus / Chroma）"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]
    raw_items = [
        {
            "source_type": "arxiv",
            "title": "AR-RAG: Autoregressive Retrieval Augmentation for Image Generation",
            "url": "https://arxiv.org/abs/2506.06962",
            "snippet": "Retrieval augmented generation for image generation systems.",
            "published_at": "2025-06-01",
        },
        {
            "source_type": "github",
            "title": "facebookresearch/faiss",
            "url": "https://github.com/facebookresearch/faiss",
            "snippet": "A library for efficient similarity search and clustering of dense vectors.",
            "published_at": "2025-01-01",
        },
        {
            "source_type": "web",
            "title": "Milvus Documentation",
            "url": "https://milvus.io/docs/overview.md",
            "snippet": "Milvus is a vector database built for embedding similarity search and AI applications.",
            "published_at": "2025-01-01",
        },
    ]

    selected, rejected, stats = select_sources_for_task(raw_items, task, per_task_limit=4)

    assert [item["title"] for item in selected] == [
        "facebookresearch/faiss",
        "Milvus Documentation",
    ]
    assert any(item["rejection_reason"] in {"weak_aspect_support", "domain_conflict"} for item in rejected)
    assert stats["off_topic_reject_count"] == 1


def test_build_source_query_prefers_react_for_architecture_arxiv_queries():
    """ReAct 方面的 arXiv 查询应显式包含 ReAct，减少泛 multi-agent 论文污染。"""
    from research_policy import build_benchmark_tasks, build_source_query

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["ReAct / Plan-and-Execute / Multi-Agent 等主流架构"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]

    arxiv_query = build_source_query(task, "arxiv")

    assert "react" in arxiv_query.lower()
    assert "multi" in arxiv_query.lower()
    assert "agent" in arxiv_query.lower()


def test_framework_comparison_query_bundle_prefers_official_docs_and_orgs():
    """框架对比任务应优先生成官方 docs 与官方 org 查询。"""
    from research_policy import build_benchmark_tasks, build_source_queries

    topic = TopicSpec(
        id="T01",
        topic="2024年大语言模型Agent架构的最新进展",
        expected_aspects=["LangGraph / CrewAI AutoGen 等框架对比"],
        min_sources=5,
        min_words=3000,
    )
    task = build_benchmark_tasks(topic)[0]

    web_queries = build_source_queries(task, "web")
    github_queries = build_source_queries(task, "github")

    assert any("site:docs.langchain.com" in query for query in web_queries)
    assert any("site:docs.crewai.com" in query for query in web_queries)
    assert any("site:microsoft.github.io" in query for query in web_queries)
    assert any("org:langchain-ai" in query for query in github_queries)
    assert any("org:crewaiinc" in query.lower() for query in github_queries)
    assert any("org:microsoft" in query for query in github_queries)


def test_match_follow_up_task_prefers_exact_case_study_aspect_over_generic_agent_keyword():
    """case-study 的 follow-up query 不应被 ReAct 任务中的通用 agent 关键词抢走。"""
    from legacy.agents.researcher import _match_follow_up_task

    tasks = [
        TaskItem(
            id=1,
            title="ReAct",
            intent="重点覆盖方面：ReAct / Plan-and-Execute / Multi-Agent 等主流架构",
            query="2024年大语言模型Agent架构的最新进展 ReAct / Plan-and-Execute / Multi-Agent 等主流架构",
            expected_aspects=["ReAct / Plan-and-Execute / Multi-Agent 等主流架构"],
            task_type="research",
        ),
        TaskItem(
            id=5,
            title="行业应用案例",
            intent="重点覆盖方面：行业应用案例",
            query="2024年大语言模型Agent架构的最新进展 行业应用案例",
            expected_aspects=["行业应用案例"],
            task_type="product",
        ),
    ]

    query = "2024年大语言模型Agent架构的最新进展 行业应用案例 agent llm function calling official case study customer story deployment production use"

    matched = _match_follow_up_task(query, tasks)

    assert matched is not None
    assert matched.title == "行业应用案例"


def test_framework_official_docs_have_high_trust_and_video_is_low_trust():
    """官方框架文档应提升为高可信，视频类结果应显著降权。"""
    from legacy.agents.researcher import _infer_trust_tier

    assert _infer_trust_tier({"source_type": "web", "url": "https://docs.langchain.com/oss/python/langgraph/overview"}) == 4
    assert _infer_trust_tier({"source_type": "web", "url": "https://docs.crewai.com/en/introduction"}) == 4
    assert _infer_trust_tier({"source_type": "web", "url": "https://microsoft.github.io/autogen/stable/index.html"}) == 4
    assert _infer_trust_tier({"source_type": "web", "url": "https://www.youtube.com/watch?v=demo"}) == 1


def test_case_study_follow_up_queries_keep_aspect_phrase_for_site_searches():
    """case-study 的 site: rescue query 也应保留方面短语，避免被别的 task 抢走。"""
    from research_policy import _build_follow_up_queries

    task = TaskItem(
        id=5,
        title="行业应用案例",
        intent="重点覆盖方面：行业应用案例",
        query="2024年大语言模型Agent架构的最新进展 行业应用案例",
        expected_aspects=["行业应用案例"],
        task_type="product",
    )

    queries = _build_follow_up_queries(
        "2024年大语言模型Agent架构的最新进展",
        "行业应用案例",
        [task],
    )

    site_queries = [query for query in queries if "site:" in query]

    assert site_queries
    assert all("行业应用案例" in query for query in site_queries)


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


def test_build_benchmark_report_core_claim_prefers_direct_high_trust_sources():
    """核心结论引用应优先使用 direct-support 的高可信来源，而不是泛背景来源。"""
    from research_policy import build_benchmark_report

    tasks = [
        TaskItem(
            id=1,
            title="向量数据库选型",
            intent="解释向量数据库选型",
            query="RAG 向量数据库选型",
            expected_aspects=["向量数据库选型（FAISS / Milvus / Chroma）"],
            task_type="research",
        )
    ]
    summaries = [
        (
            "### 核心结论\n\n"
            "本节覆盖方面：向量数据库选型（FAISS / Milvus / Chroma）。已检索到高可信来源，但它们主要提供背景信息而非直接证据，因此当前只能做出保守判断。\n\n"
            "### 证据限制\n\n"
            "当前仍需进一步验证。"
        )
    ]
    sources = [
        SourceRecord(
            citation_id=1,
            source_type="arxiv",
            query="q",
            title="Generic RAG Survey",
            url="https://arxiv.org/abs/2501.00001",
            selected=True,
            trust_tier=4,
            metadata={"support_specificity": 0.24},
            task_title="向量数据库选型",
        ),
        SourceRecord(
            citation_id=2,
            source_type="github",
            query="q",
            title="facebookresearch/faiss",
            url="https://github.com/facebookresearch/faiss",
            selected=True,
            trust_tier=5,
            metadata={"support_specificity": 0.82},
            task_title="向量数据库选型",
        ),
    ]
    evidence_notes = [
        EvidenceNote(
            task_id=1,
            task_title="向量数据库选型",
            query="RAG 向量数据库选型",
            summary=summaries[0],
            source_ids=[1, 2],
            selected_source_ids=[1, 2],
        )
    ]

    report = build_benchmark_report(
        topic="RAG（检索增强生成）技术的原理和应用",
        tasks=tasks,
        task_summaries=summaries,
        sources=sources,
        evidence_notes=evidence_notes,
    )

    section = report.split("## 1. 向量数据库选型", maxsplit=1)[1].split("## 总结", maxsplit=1)[0]
    assert "[2]" in section
    assert "[1]" not in section.split("### 核心结论", maxsplit=1)[1].split("### 证据限制", maxsplit=1)[0]
