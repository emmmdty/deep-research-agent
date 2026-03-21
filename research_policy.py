"""Benchmark profile 下的确定性研究策略。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from configs.settings import get_settings


_ASCII_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "vs",
    "with",
}

_WEAK_EVIDENCE_MARKERS = (
    "证据有限",
    "仍需进一步验证",
    "需进一步验证",
    "阶段性判断",
    "应谨慎采信",
    "保守判断",
)

_DEFAULT_CASE_STUDY_DOMAINS = [
    "openai.com",
    "anthropic.com",
    "langchain.com",
    "microsoft.com",
    "learn.microsoft.com",
    "aws.amazon.com",
    "cloud.google.com",
    "salesforce.com",
    "ibm.com",
    "huggingface.co",
]

_DEFAULT_CASE_STUDY_ORGS = {
    "openai.com": ["openai"],
    "anthropic.com": ["anthropics"],
    "langchain.com": ["langchain-ai"],
    "microsoft.com": ["microsoft", "azure-samples"],
    "learn.microsoft.com": ["microsoft", "azure-samples"],
    "aws.amazon.com": ["aws-samples", "awslabs"],
    "cloud.google.com": ["googlecloudplatform"],
    "salesforce.com": ["salesforce"],
    "ibm.com": ["ibm"],
    "huggingface.co": ["huggingface"],
}

_FRAMEWORK_OFFICIAL_DOMAINS = {
    "langgraph": ["docs.langchain.com", "reference.langchain.com"],
    "crewai": ["docs.crewai.com", "crewai.com"],
    "autogen": ["microsoft.github.io", "microsoft.com"],
}

_FRAMEWORK_OFFICIAL_ORGS = {
    "langgraph": ["langchain-ai"],
    "crewai": ["crewAIInc"],
    "autogen": ["microsoft"],
}


def is_case_study_aspect(aspect: str) -> bool:
    """判断某个方面是否要求真实落地案例，而不是泛背景介绍。"""
    normalized = normalize_text(aspect)
    return any(
        marker in normalized
        for marker in (
            "行业应用案例",
            "应用案例",
            "case study",
            "use case",
            "production application",
            "deployment",
            "customer story",
        )
    )


def normalize_text(text: str) -> str:
    """统一文本归一化，便于做确定性匹配。"""
    normalized = (text or "").lower()
    normalized = re.sub(r"[\(\)\[\]{}（）【】<>《》,，。:：;；!！?？/\\|+*_=-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def tokenize_text(text: str) -> list[str]:
    """把文本拆成英文词与中文短语。"""
    normalized = normalize_text(text)
    if not normalized:
        return []

    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
    expanded: list[str] = []
    for token in tokens:
        if re.fullmatch(r"[a-z0-9]+", token):
            if token not in _ASCII_STOPWORDS and len(token) > 1:
                expanded.append(token)
        else:
            expanded.append(token)
    return expanded


def extract_aspect_keywords(aspect: str) -> list[str]:
    """从方面文本中抽取关键字。"""
    normalized = normalize_text(aspect)
    variants = set(tokenize_text(normalized))

    for fragment in re.split(r"\s+", normalized):
        if fragment and fragment not in _ASCII_STOPWORDS and len(fragment) > 1:
            variants.add(fragment)

    if "plan and execute" in normalized:
        variants.update({"plan", "execute"})
    if "multi agent" in normalized:
        variants.update({"multi", "agent"})
    if "chunking" in normalized:
        variants.add("chunk")

    return sorted(variants)


def aspect_hits_in_text(text: str, aspects: list[str]) -> list[str]:
    """判断文本命中的 expected aspects。"""
    normalized = normalize_text(text)
    hits: list[str] = []
    for aspect in aspects:
        keywords = extract_aspect_keywords(aspect)
        if not keywords:
            continue
        matched = [keyword for keyword in keywords if keyword in normalized]
        threshold = 1 if len(keywords) <= 2 else max(2, int(len(keywords) * 0.6 + 0.999))
        if len(matched) >= threshold:
            hits.append(aspect)
    return hits


def infer_task_type(topic: str) -> str:
    """根据主题推断任务类型。"""
    normalized = normalize_text(topic)
    if any(keyword in normalized for keyword in {"安装", "教程", "guide", "setup", "how to", "quick start"}):
        return "tutorial"
    if any(keyword in normalized for keyword in {"对比", "比较", "vs", "difference"}):
        return "comparison"
    if any(keyword in normalized for keyword in {"组织", "社区", "公司", "是什么样"}):
        return "organization"
    if any(keyword in normalized for keyword in {"应用案例", "案例", "产品"}):
        return "product"
    return "research"


def preferred_sources_for_task(task_type: str) -> list[str]:
    """任务类型对应的默认来源策略。"""
    if task_type in {"tutorial", "organization", "product"}:
        return ["web", "github"]
    return ["web", "arxiv", "github"]


def _resolve_task_type_for_aspect(task_type: str, aspect: str) -> str:
    """按方面细化任务类型，允许在 research 主题中派生出 product/case-study 子任务。"""
    if is_case_study_aspect(aspect):
        return "product"
    return task_type


def preferred_sources_for_aspect(task_type: str, aspect: str) -> list[str]:
    """按具体方面选择更可靠的默认来源组合。"""
    task_type = _resolve_task_type_for_aspect(task_type, aspect)
    base_sources = preferred_sources_for_task(task_type)
    normalized = normalize_text(aspect)
    if task_type in {"tutorial", "organization", "product"}:
        return base_sources

    abstract_architecture_markers = (
        "react",
        "plan-and-execute",
        "multi-agent",
    )
    concrete_stack_markers = (
        "langgraph",
        "crewai",
        "autogen",
        "faiss",
        "milvus",
        "chroma",
        "chunking",
        "embedding",
        "faithfulness",
        "relevance",
        "recall",
        "tool calling",
        "function calling",
    )
    if any(marker in normalized for marker in abstract_architecture_markers):
        return ["web", "arxiv"]
    if any(marker in normalized for marker in concrete_stack_markers):
        return ["web", "github"]
    return base_sources


def should_use_source(task_type: str, source_name: str) -> bool:
    """判断任务类型是否启用某种来源。"""
    return source_name in preferred_sources_for_task(task_type)


def build_benchmark_tasks(topic_spec) -> list[Any]:
    """根据 TopicSpec 生成稳定的 benchmark 任务。"""
    from workflows.states import TaskItem

    task_type = infer_task_type(topic_spec.topic)
    tasks: list[TaskItem] = []

    for index, aspect in enumerate(topic_spec.expected_aspects or [topic_spec.topic], start=1):
        task_type_for_aspect = _resolve_task_type_for_aspect(task_type, aspect)
        query = _build_query(topic_spec.topic, aspect, task_type_for_aspect)
        preferred_sources = preferred_sources_for_aspect(task_type_for_aspect, aspect)
        tasks.append(
            TaskItem(
                id=index,
                title=_task_title_from_aspect(aspect),
                intent=f"重点覆盖方面：{aspect}",
                query=query,
                task_type=task_type_for_aspect,
                expected_aspects=[aspect],
                preferred_sources=preferred_sources,
                must_include_terms=_aspect_required_terms(aspect, task_type_for_aspect, topic_spec.topic),
                avoid_terms=["arxiv"] if task_type_for_aspect in {"tutorial", "product"} else [],
            )
        )
    return tasks


def build_source_query(task, source_name: str) -> str:
    """为不同来源构造更稳健的查询语句。"""
    queries = build_source_queries(task, source_name)
    return queries[0] if queries else ""


def build_source_queries(task, source_name: str) -> list[str]:
    """为不同来源构造查询包；case-study 任务使用官方域名优先的多模板召回。"""
    aspect = (task.expected_aspects or [task.title])[0]
    task_type = _resolve_task_type_for_aspect(
        getattr(task, "task_type", infer_task_type(task.query)),
        aspect,
    )
    if task_type == "product":
        return _build_case_study_query_bundle(task, source_name)
    if _is_framework_comparison_aspect(aspect):
        return _build_framework_comparison_query_bundle(task, source_name)

    query = _build_single_source_query(task, source_name, task_type=task_type, aspect=aspect)
    return [query] if query else []


def _build_single_source_query(task, source_name: str, *, task_type: str, aspect: str) -> str:
    """构造单条来源查询。"""
    topic_aliases = _topic_alias_terms(task.query)
    semantic_terms = _aspect_semantic_terms(aspect, task_type)
    focus_terms = _dedupe_terms(
        [*semantic_terms[:8], *topic_aliases, *_aspect_boost_terms(aspect, task_type)]
    )
    base_terms = [task.query]
    aspect_terms = _aspect_boost_terms(aspect, task_type)

    if source_name == "github":
        if task_type == "product":
            github_focus = _dedupe_terms(
                [
                    *(_ascii_query_terms(_topic_alias_terms(task.query))[:2] or ["agent"]),
                    "agent",
                    "case study",
                    "production",
                    "application",
                    "example",
                    "project",
                ]
            )
        else:
            github_focus = _ascii_query_terms(focus_terms) or _ascii_query_terms(semantic_terms) or [task.title]
        return _compact_query(github_focus[:6])
    elif source_name == "arxiv":
        if task_type in {"tutorial", "product", "organization"}:
            return task.query
        arxiv_focus = _ascii_query_terms(focus_terms) or _ascii_query_terms(semantic_terms) or [task.title]
        return _compact_query([*arxiv_focus[:6], "paper", "survey", "benchmark"])
    else:
        base_terms.extend([*topic_aliases, "official documentation"])

    if task_type == "product":
        base_terms.extend(["case study", "customer story", "deployment", "production use", "product blog"])
    if task_type == "tutorial":
        base_terms.extend(["install", "setup", "quick start"])

    return _compact_query([*base_terms, *aspect_terms])


def _build_case_study_query_bundle(task, source_name: str) -> list[str]:
    """为 case-study 任务生成多模板查询。"""
    aspect = (task.expected_aspects or [task.title])[0]
    topic_text = getattr(task, "query", "") or getattr(task, "title", "")
    family_terms = _case_study_topic_family_terms(topic_text)
    aspect_terms = _aspect_boost_terms(aspect, "product")
    aspect_ascii_terms = _ascii_query_terms(aspect_terms)[:4]
    aspect_ascii_text = _compact_query(aspect_ascii_terms)
    family_text = _compact_query(family_terms or ["agent"])
    official_domains = _case_study_domains_for_topic(topic_text)
    official_orgs = _case_study_official_orgs(official_domains)
    queries: list[str] = []

    if source_name == "web":
        queries.append(
            _compact_query(
                [
                    topic_text,
                    aspect,
                    aspect_ascii_text,
                    family_text,
                    "official",
                    "case study",
                    "customer story",
                    "deployment",
                    "production use",
                ]
            )
        )
        for domain in official_domains[:4]:
            queries.append(
                _compact_query(
                    [
                        topic_text,
                        aspect,
                        aspect_ascii_text,
                        f"site:{domain}",
                        family_text,
                        "case study",
                        "customer story",
                        "deployment",
                        "production",
                    ]
                )
            )
        queries.append(
            _compact_query([topic_text, aspect_ascii_text, family_text, "product blog", "customer story", "production"])
        )
    elif source_name == "github":
        generic_terms = _dedupe_terms([aspect_ascii_text, family_text, "example", "project", "production", "deployment"])
        queries.append(_compact_query(generic_terms))
        for org in official_orgs[:4]:
            queries.append(
                _compact_query(
                    [
                        f"org:{org}",
                        aspect_ascii_text,
                        family_text,
                        "example",
                        "project",
                        "production",
                    ]
                )
            )
    else:
        queries.append(_build_single_source_query(task, source_name, task_type="product", aspect=aspect))

    deduped = [query for query in _dedupe_terms(queries) if query]
    return deduped


def _is_framework_comparison_aspect(aspect: str) -> bool:
    normalized = normalize_text(aspect)
    return "comparison" in normalized or "对比" in normalized or any(
        marker in normalized for marker in ("langgraph", "crewai", "autogen")
    )


def _framework_keywords(aspect: str) -> list[str]:
    normalized = normalize_text(aspect)
    keywords: list[str] = []
    for marker in ("langgraph", "crewai", "autogen"):
        if marker in normalized:
            keywords.append(marker)
    return keywords or ["langgraph", "crewai", "autogen"]


def _build_framework_comparison_query_bundle(task, source_name: str) -> list[str]:
    """为框架对比任务生成官方文档与官方 org 优先的查询包。"""
    aspect = (task.expected_aspects or [task.title])[0]
    topic_text = getattr(task, "query", "") or getattr(task, "title", "")
    keywords = _framework_keywords(aspect)
    queries: list[str] = []

    if source_name == "web":
        queries.append(
            _compact_query(
                [topic_text, aspect, "official documentation", "framework comparison"]
            )
        )
        for keyword in keywords:
            for domain in _FRAMEWORK_OFFICIAL_DOMAINS.get(keyword, []):
                queries.append(
                    _compact_query(
                        [
                            topic_text,
                            aspect,
                            f"site:{domain}",
                            keyword,
                            "official documentation",
                            "framework",
                        ]
                    )
                )
    elif source_name == "github":
        queries.append(
            _compact_query([*keywords, "agent framework", "comparison"])
        )
        for keyword in keywords:
            for org in _FRAMEWORK_OFFICIAL_ORGS.get(keyword, []):
                queries.append(
                    _compact_query(
                        [
                            f"org:{org}",
                            keyword,
                            "agent framework",
                        ]
                    )
                )
    else:
        queries.append(_build_single_source_query(task, source_name, task_type="comparison", aspect=aspect))

    return [query for query in _dedupe_terms(queries) if query]


def _task_title_from_aspect(aspect: str) -> str:
    normalized = normalize_text(aspect)
    if "依赖" in normalized or "前置条件" in normalized:
        return "依赖与前置条件"
    if "安装" in normalized:
        return "安装步骤与配置"
    if "错误" in normalized or "排查" in normalized:
        return "常见错误与排查"
    if "验证" in normalized or "运行" in normalized:
        return "验证与快速开始"
    return aspect.split("/")[0].strip()


def _build_query(topic: str, aspect: str, task_type: str) -> str:
    base = f"{topic} {aspect}".strip()
    normalized_aspect = normalize_text(aspect)
    if task_type == "tutorial":
        if "依赖" in normalized_aspect or "前置条件" in normalized_aspect:
            return f"{base} installation requirements dependencies prerequisites"
        if "安装" in normalized_aspect:
            return f"{base} install tutorial setup guide windows linux"
        if "错误" in normalized_aspect or "排查" in normalized_aspect:
            return f"{base} installation problems troubleshooting errors"
        if "验证" in normalized_aspect or "运行" in normalized_aspect:
            return f"{base} quick start getting started example"
        return f"{base} official documentation source code"
    if task_type == "product":
        return f"{base} official case study customer story deployment production use"
    if task_type == "comparison":
        return f"{base} comparison benchmark differences"
    return _compact_query([base, *_aspect_boost_terms(aspect, task_type)])


def _aspect_boost_terms(aspect: str, task_type: str) -> list[str]:
    normalized = normalize_text(aspect)
    boosts: list[str] = []
    if "接入模式" in normalized or ("接入" in normalized and "模式" in normalized):
        boosts.extend(["integration pattern", "tool integration", "transport", "stdio", "sse", "streamable http"])
    if "错误恢复" in normalized:
        boosts.extend(["error handling", "retry", "fallback", "reconnect", "recovery"])
    if "监管" in normalized:
        boosts.extend(["regulatory", "regulation", "governance", "policy control"])
    if "智能投顾" in normalized:
        boosts.extend(["robo advisor", "wealth management", "investment advisory"])
    if "量化交易" in normalized:
        boosts.extend(["quantitative trading", "algorithmic trading"])
    if "风控" in normalized:
        boosts.extend(["risk management", "risk control"])
    if "反欺诈" in normalized:
        boosts.extend(["fraud detection", "anti fraud"])
    if "客户服务" in normalized:
        boosts.extend(["customer service", "contact center", "support agent"])
    if "合规" in normalized:
        boosts.extend(["compliance", "regulatory compliance", "aml", "kyc"])
    if "效果数据" in normalized or "效果" in normalized:
        boosts.extend(["roi", "cost reduction", "productivity", "efficiency"])
    if "memory" in normalized or "记忆" in normalized:
        boosts.extend(["memory", "long-term memory", "episodic memory"])
    if "tool calling" in normalized or "function calling" in normalized or "工具" in normalized:
        boosts.extend(["tool calling", "function calling"])
    if "框架" in normalized or "langgraph" in normalized or "crewai" in normalized or "autogen" in normalized:
        boosts.extend(["LangGraph", "CrewAI", "AutoGen", "comparison"])
    if is_case_study_aspect(aspect):
        boosts.extend(["case study", "customer story", "deployment", "production use"])
    if "评估指标" in normalized or any(token in normalized for token in {"faithfulness", "relevance", "recall"}):
        boosts.extend(["evaluation", "faithfulness", "relevance", "recall"])
    if "chunking" in normalized or "embedding" in normalized:
        boosts.extend(["chunking", "embedding", "retrieval"])
    if task_type == "research" and not boosts:
        boosts.extend(["survey", "official docs"])
    return boosts


def _aspect_required_terms(aspect: str, task_type: str, topic: str) -> list[str]:
    normalized = normalize_text(aspect)
    terms = list(tokenize_text(aspect)[:4])
    terms.extend(_topic_alias_terms(topic))
    terms.extend(_aspect_semantic_terms(aspect, task_type))
    if task_type == "tutorial":
        if "依赖" in normalized or "前置条件" in normalized:
            terms.extend(["dependency", "dependencies", "requirements", "prerequisites"])
        if "下载" in normalized or "源码" in normalized:
            terms.extend(["download", "source", "clone", "repository"])
        if "编译" in normalized or "步骤" in normalized:
            terms.extend(["install", "setup", "build", "quickstart"])
        if "错误" in normalized or "排查" in normalized:
            terms.extend(["troubleshooting", "error", "issue", "fix"])
        if "运行" in normalized or "验证" in normalized:
            terms.extend(["quick", "start", "verify", "health"])
    else:
        terms.extend(_aspect_anchor_terms(aspect))
        if "framework" in normalized or "框架" in normalized:
            terms.extend(["framework", "agent framework"])
        if "tool calling" in normalized or "function calling" in normalized or "工具" in normalized:
            terms.extend(["tool calling", "function calling", "mcp"])
        if "memory" in normalized or "记忆" in normalized:
            terms.extend(["memory", "episodic memory", "long-term memory"])
        if task_type == "product" or is_case_study_aspect(aspect):
            terms.extend(["case study", "customer story", "deployment", "production", "application"])
    return _dedupe_terms(terms)


def _aspect_semantic_terms(aspect: str, task_type: str) -> list[str]:
    """为具体方面补充更适合检索和判定的双语语义词。"""
    normalized = normalize_text(aspect)
    terms = list(_aspect_anchor_terms(aspect))

    if "接入模式" in normalized or ("接入" in normalized and "模式" in normalized):
        terms.extend(["integration pattern", "tool integration", "transport", "stdio", "sse", "streamable http"])
    if "错误恢复" in normalized:
        terms.extend(["error handling", "retry", "fallback", "reconnect", "recovery"])
    if "监管" in normalized:
        terms.extend(["regulatory", "regulation", "governance", "policy control"])
    if "智能投顾" in normalized:
        terms.extend(["robo advisor", "wealth management", "investment advisory"])
    if "量化交易" in normalized:
        terms.extend(["quantitative trading", "algorithmic trading"])
    if "风控" in normalized:
        terms.extend(["risk management", "risk control"])
    if "反欺诈" in normalized:
        terms.extend(["fraud detection", "anti fraud"])
    if "客户服务" in normalized:
        terms.extend(["customer service", "contact center", "support agent", "virtual assistant"])
    if "合规" in normalized:
        terms.extend(["compliance", "regulatory compliance", "aml", "kyc"])
    if "效果数据" in normalized or "效果" in normalized:
        terms.extend(["roi", "cost reduction", "productivity", "efficiency", "accuracy"])

    if task_type == "tutorial":
        if "依赖" in normalized or "前置条件" in normalized:
            terms.extend(["dependency", "dependencies", "requirements", "prerequisites", "install requirements"])
        if "安装" in normalized or "步骤" in normalized or "编译" in normalized:
            terms.extend(["install", "setup", "build", "quick start"])
        if "错误" in normalized or "排查" in normalized:
            terms.extend(["troubleshooting", "error", "issue", "fix"])
        if "运行" in normalized or "验证" in normalized:
            terms.extend(["verify", "validation", "quick start", "getting started"])

    if "检索" in normalized or "生成" in normalized:
        terms.extend(["retrieval", "generation"])
    if is_case_study_aspect(aspect) or task_type == "product":
        terms.extend(["case study", "customer story", "deployment", "production", "application"])
    if "向量数据库" in normalized:
        terms.extend(["vector database", "faiss", "milvus", "chroma"])
    if "chunking" in normalized or "分块" in normalized:
        terms.extend(["chunking", "text splitting"])
    if "embedding" in normalized or "向量化" in normalized:
        terms.extend(["embedding", "embedding model"])
    if "faithfulness" in normalized or "relevance" in normalized or "recall" in normalized or "评估指标" in normalized:
        terms.extend(["faithfulness", "relevance", "recall", "evaluation"])
    if "langgraph" in normalized or "crewai" in normalized or "autogen" in normalized:
        terms.extend(["langgraph", "crewai", "autogen", "agent framework"])
    if "react" in normalized or "plan-and-execute" in normalized or "multi-agent" in normalized:
        terms.extend(["ReAct", "react", "reasoning and acting", "plan-and-execute", "multi-agent"])
    if "memory" in normalized or "长期记忆" in normalized or "记忆" in normalized:
        terms.extend(["memory", "long-term memory", "episodic memory"])
    if "tool calling" in normalized or "function calling" in normalized or "工具" in normalized:
        terms.extend(["tool calling", "function calling", "tool use"])
    if task_type == "research" and not terms:
        terms.extend(_aspect_boost_terms(aspect, task_type))
    return _dedupe_terms(terms)


def _ascii_query_terms(terms: list[str]) -> list[str]:
    """优先保留 GitHub / arXiv 更易命中的英文检索词。"""
    picked: list[str] = []
    for term in terms:
        normalized = normalize_text(term)
        if not normalized:
            continue
        if re.fullmatch(r"[a-z0-9][a-z0-9\-\s/+.]*", normalized):
            picked.append(term)
    return _dedupe_terms(picked)


def _dedupe_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.lower()
        if key not in seen:
            deduped.append(term)
            seen.add(key)
    return deduped


def _compact_query(parts: list[str]) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for token in str(part).split():
            key = token.lower()
            if key not in seen:
                tokens.append(token)
                seen.add(key)
    return " ".join(tokens).strip()


def select_sources_for_task(
    raw_items: list[dict[str, Any]],
    task,
    *,
    per_task_limit: int = 6,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """按相关性、可信度和锚点一致性筛选来源。"""
    aspect = (getattr(task, "expected_aspects", None) or [getattr(task, "title", "")])[0]
    case_study_task = is_case_study_aspect(aspect) or getattr(task, "task_type", "research") == "product"
    query_tokens = set(tokenize_text(task.query))
    task_tokens = set(tokenize_text(task.title)) | set(tokenize_text(" ".join(task.expected_aspects)))
    stats = {"off_topic_reject_count": 0, "duplicate_reject_count": 0}
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    required_tokens = set(getattr(task, "must_include_terms", []) or [])
    avoid_tokens = set(getattr(task, "avoid_terms", []) or [])
    topic_guard_terms = _topic_guard_terms(task.query)

    anchor_tokens = _derive_anchor_tokens(raw_items)

    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in raw_items:
        title = item.get("title", "")
        url = item.get("url", "")
        dedupe_key = (normalize_text(title), normalize_text(url))
        if dedupe_key in seen_keys:
            item["rejection_reason"] = "duplicate"
            rejected.append(item)
            stats["duplicate_reject_count"] += 1
            continue
        seen_keys.add(dedupe_key)

        normalized_text = normalize_text(f"{item.get('title', '')} {item.get('snippet', '')}")
        aspect_specificity = _aspect_support_specificity(item, task)
        item["support_specificity"] = round(aspect_specificity, 3)
        item["direct_support"] = aspect_specificity >= _direct_support_threshold(task, item)
        if _is_withdrawn_source(item):
            item["rejection_reason"] = "withdrawn"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue

        text_tokens = set(tokenize_text(f"{item.get('title', '')} {item.get('snippet', '')}"))
        if topic_guard_terms and not _matches_guard_terms(normalized_text, topic_guard_terms):
            case_study_override = False
            if case_study_task:
                case_study_preview = _classify_case_study_item(item, task)
                case_study_override = bool(case_study_preview.get("case_study_evidence"))
            if case_study_override or aspect_specificity >= _topic_guard_override_threshold(task, item):
                pass
            else:
                item["rejection_reason"] = "topic_guard_miss"
                rejected.append(item)
                stats["off_topic_reject_count"] += 1
                continue
        entity_conflict_reason = _entity_conflict_reason(task.query, normalized_text)
        if entity_conflict_reason:
            item["rejection_reason"] = entity_conflict_reason
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        domain_conflict_reason = _domain_conflict_reason(task.query, normalized_text, item)
        if domain_conflict_reason:
            item["rejection_reason"] = domain_conflict_reason
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        if case_study_task:
            case_study_meta = _classify_case_study_item(item, task)
            item.update(case_study_meta)
            if not item["case_study_evidence"]:
                item["rejection_reason"] = (
                    "case_study_topic_miss"
                    if item.get("case_study_type") != "not_case_study" and not item.get("matches_topic_family")
                    else "not_case_study_evidence"
                )
                rejected.append(item)
                stats["off_topic_reject_count"] += 1
                continue
        if required_tokens and not _matches_required_terms(text_tokens, normalized_text, required_tokens):
            item["rejection_reason"] = "missing_required_terms"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        if aspect_specificity < _minimum_support_specificity(task, item):
            item["rejection_reason"] = "weak_aspect_support"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        if avoid_tokens and (text_tokens & avoid_tokens):
            item["rejection_reason"] = "contains_avoid_terms"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue

        score = _score_source_item(
            item,
            query_tokens=query_tokens,
            task_tokens=task_tokens,
            anchor_tokens=anchor_tokens,
            support_specificity=aspect_specificity,
        )
        item["selection_score"] = round(score, 3)
        if score < 0.30:
            item["rejection_reason"] = "off_topic"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        ranked.append((score, item))

    ranked_sorted = sorted(ranked, key=lambda pair: pair[0], reverse=True)
    source_counts: Counter[str] = Counter()
    selected_ids: set[int] = set()
    high_trust_target = min(max(1, per_task_limit // 2), len([item for _, item in ranked_sorted if _trust_tier(item) >= 4]))

    for _, item in ranked_sorted:
        if len(selected) >= high_trust_target:
            break
        if _trust_tier(item) < 4:
            continue
        source_name = item.get("source_type", "web")
        if source_counts[source_name] >= 3:
            continue
        selected.append(item)
        selected_ids.add(id(item))
        source_counts[source_name] += 1

    for _, item in ranked_sorted:
        if len(selected) >= per_task_limit:
            break
        if id(item) in selected_ids:
            continue
        source_name = item.get("source_type", "web")
        if source_counts[source_name] >= 3:
            continue
        selected.append(item)
        selected_ids.add(id(item))
        source_counts[source_name] += 1

    return selected, rejected, stats


def _derive_anchor_tokens(raw_items: list[dict[str, Any]]) -> set[str]:
    trusted = [item for item in raw_items if item.get("source_type") in {"github", "arxiv"}]
    if not trusted:
        return set()

    trusted.sort(key=lambda item: _trust_tier(item), reverse=True)
    anchor_text = " ".join(f"{item.get('title', '')} {item.get('snippet', '')}" for item in trusted[:2])
    counts = Counter(tokenize_text(anchor_text))
    return {token for token, _ in counts.most_common(8)}


def _score_source_item(
    item: dict[str, Any],
    *,
    query_tokens: set[str],
    task_tokens: set[str],
    anchor_tokens: set[str],
    support_specificity: float,
) -> float:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    text = f"{title} {snippet}"
    text_tokens = set(tokenize_text(text))
    trust = _trust_tier(item) / 5
    overlap = _overlap_score(text_tokens, query_tokens | task_tokens)
    anchor_score = _overlap_score(text_tokens, anchor_tokens) if anchor_tokens else 0.5
    recency = _recency_score(item)
    case_study_strength = float(item.get("case_study_strength_score", 0.0) or 0.0)
    if case_study_strength > 0:
        return (
            0.22 * overlap
            + 0.23 * trust
            + 0.10 * anchor_score
            + 0.08 * recency
            + 0.17 * support_specificity
            + 0.20 * case_study_strength
        )
    return 0.30 * overlap + 0.30 * trust + 0.15 * anchor_score + 0.10 * recency + 0.15 * support_specificity


def _trust_tier(item: dict[str, Any] | Any) -> int:
    trust_override = getattr(item, "trust_tier_override", None)
    if trust_override is None and isinstance(item, dict):
        trust_override = item.get("trust_tier_override")
    if trust_override is not None:
        return int(trust_override)

    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    url = getattr(item, "url", None) or item.get("url", "")
    normalized_url = url.lower()

    if source_type == "github":
        return 5
    if source_type == "arxiv":
        return 4
    if any(
        marker in normalized_url
        for marker in (
            "docs.langchain.com",
            "reference.langchain.com",
            "docs.crewai.com",
            "crewai.com",
            "microsoft.github.io",
            "docs.",
            "readthedocs",
            "aws.amazon.com",
            "milvus.io",
            "platform.openai.com",
            "python.langchain.com",
            "docs.gptr.dev",
            "langchain.com",
            "microsoft.com",
        )
    ):
        return 4
    if any(
        marker in normalized_url
        for marker in ("case-study", "case_study", "customer-story", "customer_story", "success-story", "deployment")
    ):
        return 4
    if any(marker in normalized_url for marker in ("cnblogs.com", "csdn.net", "zhihu.com", "heartthinkdo.com", "smallyoung.cn")):
        return 2
    if any(marker in normalized_url for marker in ("youtube.com", "youtu.be", "bilibili.com")):
        return 1
    if any(marker in normalized_url for marker in ("reddit.com", "facebook.com", "x.com")):
        return 1
    return 3


def _recency_score(item: dict[str, Any] | Any) -> float:
    published_at = getattr(item, "published_at", None) or item.get("published_at")
    if not published_at:
        return 0.6
    match = re.match(r"(\d{4})", str(published_at))
    if not match:
        return 0.6
    year = int(match.group(1))
    if year >= 2024:
        return 1.0
    if year >= 2021:
        return 0.8
    if year >= 2018:
        return 0.5
    return 0.2


def _topic_alias_terms(topic: str) -> list[str]:
    normalized = normalize_text(topic)
    aliases: list[str] = []
    if "mcp" in normalized or "model context protocol" in normalized:
        aliases.extend(["MCP", "Model Context Protocol"])
    if "大语言模型" in normalized or "llm" in normalized or "language model" in normalized:
        aliases.extend(["LLM", "language model"])
    if "agent" in normalized or "智能体" in normalized:
        aliases.extend(["agent", "agent architecture"])
    if "rag" in normalized or "检索增强生成" in normalized or "retrieval augmented generation" in normalized:
        aliases.extend(["RAG", "retrieval augmented generation"])
    if "openclaw" in normalized:
        aliases.extend(["OpenClaw", "Captain Claw"])
    return _dedupe_terms(aliases)


def _case_study_official_domains() -> list[str]:
    try:
        settings = get_settings()
        domains = list(getattr(settings, "case_study_official_domains", []) or [])
        if domains:
            return domains
    except Exception:
        pass
    return list(_DEFAULT_CASE_STUDY_DOMAINS)


def _case_study_official_orgs(domains: list[str] | None = None) -> list[str]:
    orgs: list[str] = []
    for domain in domains or _case_study_official_domains():
        orgs.extend(_DEFAULT_CASE_STUDY_ORGS.get(domain, []))
    return _dedupe_terms(orgs)


def _case_study_topic_family_terms(topic: str) -> list[str]:
    normalized = normalize_text(topic)
    if any(marker in normalized for marker in ("金融", "bank", "banking", "finance", "financial", "fraud", "合规", "风控", "投顾", "trading")):
        return [
            "financial services",
            "banking",
            "fraud detection",
            "compliance",
            "customer service",
            "agent",
            "llm",
        ]
    if "rag" in normalized or "检索增强生成" in normalized:
        return ["rag", "retrieval", "knowledge", "search"]
    if "agent" in normalized or "智能体" in normalized or "大语言模型" in normalized:
        return ["agent", "llm", "function calling"]
    return _ascii_query_terms(_topic_alias_terms(topic)) or ["ai", "agent"]


def _case_study_domains_for_topic(topic: str) -> list[str]:
    """按主题重排 case-study 官方域名优先级。"""
    normalized = normalize_text(topic)
    domains = list(_case_study_official_domains())
    if any(marker in normalized for marker in ("金融", "bank", "banking", "finance", "financial", "fraud", "合规", "风控", "投顾", "trading")):
        preferred = [
            "aws.amazon.com",
            "microsoft.com",
            "learn.microsoft.com",
            "ibm.com",
            "salesforce.com",
            "cloud.google.com",
            "openai.com",
            "anthropic.com",
            "langchain.com",
        ]
        return _dedupe_terms([*preferred, *domains])
    return domains


def _source_domain_from_item(item: dict[str, Any] | Any) -> str:
    url = getattr(item, "url", None) or (item.get("url", "") if isinstance(item, dict) else "")
    parsed = re.sub(r"^www\.", "", re.sub(r":\d+$", "", normalize_text(urlparse_url(url))))
    return parsed


def urlparse_url(url: str) -> str:
    match = re.match(r"https?://([^/]+)", url or "")
    return match.group(1).lower() if match else ""


def _is_official_case_study_domain(domain: str) -> bool:
    return any(domain == official or domain.endswith(f".{official}") for official in _case_study_official_domains())


def _extract_github_owner(item: dict[str, Any] | Any) -> str:
    owner = getattr(item, "owner", None) or (item.get("owner", "") if isinstance(item, dict) else "")
    if owner:
        return str(owner).strip().lower()
    title = getattr(item, "title", None) or (item.get("title", "") if isinstance(item, dict) else "")
    url = getattr(item, "url", None) or (item.get("url", "") if isinstance(item, dict) else "")
    if title and "/" in title:
        return title.split("/", 1)[0].strip().lower()
    match = re.search(r"github\.com/([^/]+)/", url or "", re.IGNORECASE)
    return match.group(1).lower() if match else ""


def _matches_case_study_topic_family(normalized_text: str, topic: str) -> bool:
    family_terms = _case_study_topic_family_terms(topic)
    return any(normalize_text(term) in normalized_text for term in family_terms if normalize_text(term))


def _classify_case_study_item(item: dict[str, Any] | Any, task) -> dict[str, Any]:
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    url = getattr(item, "url", None) or item.get("url", "")
    title = getattr(item, "title", None) or item.get("title", "")
    snippet = getattr(item, "snippet", None) or item.get("snippet", "")
    normalized_text = normalize_text(f"{title} {snippet} {url}")
    domain = urlparse_url(url)
    official_domain = _is_official_case_study_domain(domain)
    repo_owner = _extract_github_owner(item)
    official_repo = source_type == "github" and repo_owner in set(_case_study_official_orgs())
    negative_markers = ("survey", "review", "benchmark", "overview", "landscape", "trend")
    production_markers = ("production", "in production", "deployment", "customer story", "case study", "use case")
    example_markers = ("example", "project", "sample", "reference architecture", "starter")
    has_production_marker = any(marker in normalized_text for marker in production_markers)
    has_quantitative_outcome = bool(re.search(r"\b\d+(?:\.\d+)?\s*(%|x|倍|hours|days|minutes|小时|天|million|billion)\b", normalized_text))
    matches_topic_family = _matches_case_study_topic_family(normalized_text, getattr(task, "query", ""))

    if any(marker in normalized_text for marker in negative_markers):
        return {
            "case_study_evidence": False,
            "case_study_type": "not_case_study",
            "matches_topic_family": matches_topic_family,
            "case_study_strength_score": 0.0,
            "has_quantitative_outcome": has_quantitative_outcome,
            "trust_tier_override": 4 if official_domain else _trust_tier(item),
        }

    case_type = "not_case_study"
    if official_domain and any(marker in normalized_text for marker in ("customer story", "case study", "success story")):
        case_type = "official_customer_story"
    elif official_domain and any(marker in normalized_text for marker in ("deployment", "production", "use case", "product blog")):
        case_type = "official_product_blog"
    elif official_domain and any(marker in normalized_text for marker in ("docs", "example", "quickstart", "reference architecture")):
        case_type = "official_docs_example"
    elif official_repo and any(marker in normalized_text for marker in (*production_markers, *example_markers)):
        case_type = "first_party_repo"

    base_strength = {
        "official_customer_story": 0.9,
        "official_product_blog": 0.82,
        "official_docs_example": 0.72,
        "first_party_repo": 0.7,
        "not_case_study": 0.0,
    }.get(case_type, 0.0)
    if matches_topic_family:
        base_strength += 0.05
    if has_quantitative_outcome:
        base_strength += 0.05
    if has_production_marker:
        base_strength += 0.03

    return {
        "case_study_evidence": case_type != "not_case_study" and matches_topic_family,
        "case_study_type": case_type,
        "matches_topic_family": matches_topic_family,
        "case_study_strength_score": round(min(base_strength, 1.0), 3),
        "has_quantitative_outcome": has_quantitative_outcome,
        "has_production_marker": has_production_marker,
        "trust_tier_override": 4 if official_domain else (5 if official_repo else _trust_tier(item)),
    }


def _topic_guard_terms(topic: str) -> list[str]:
    normalized = normalize_text(topic)
    if "mcp" in normalized or "model context protocol" in normalized:
        return ["mcp", "model context protocol"]
    if "rag" in normalized or "检索增强生成" in normalized or "retrieval augmented generation" in normalized:
        return ["rag", "retrieval augmented generation", "retrieval augmented"]
    if "大语言模型" in normalized or "llm" in normalized or "language model" in normalized:
        return ["llm", "language model", "large language model"]
    if "openclaw" in normalized:
        return ["openclaw", "captain claw"]
    return []


def _aspect_anchor_terms(aspect: str) -> list[str]:
    anchors: list[str] = []
    for chunk in re.split(r"[\\/|,，；;]", aspect):
        cleaned = normalize_text(chunk)
        if not cleaned:
            continue
        if cleaned in {"等主流架构", "主流架构", "原理和应用"}:
            continue
        anchors.extend(tokenize_text(cleaned))
    return _dedupe_terms(anchors)


def _matches_required_terms(text_tokens: set[str], normalized_text: str, required_terms: set[str]) -> bool:
    for term in required_terms:
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        if " " in normalized_term:
            if normalized_term in normalized_text:
                return True
            term_tokens = set(tokenize_text(normalized_term))
            if term_tokens and term_tokens.issubset(text_tokens):
                return True
        elif normalized_term in text_tokens or normalized_term in normalized_text:
            return True
    return False


def _matches_guard_terms(normalized_text: str, guard_terms: list[str]) -> bool:
    return any(normalize_text(term) in normalized_text for term in guard_terms if normalize_text(term))


def _is_withdrawn_source(item: dict[str, Any] | Any) -> bool:
    title = (getattr(item, "title", None) or item.get("title", "")).lower()
    snippet = (getattr(item, "snippet", None) or item.get("snippet", "")).lower()
    return "withdrawn" in title or "withdrawn" in snippet


def _entity_conflict_reason(topic: str, normalized_text: str) -> str | None:
    normalized_topic = normalize_text(topic)
    if "openclaw" in normalized_topic:
        if any(marker in normalized_text for marker in ("ai agent", "assistant", "chat apps", "personal ai")):
            if not any(marker in normalized_text for marker in ("captain claw", "game", "engine")):
                return "entity_conflict"
    return None


def _domain_conflict_reason(topic: str, normalized_text: str, item: dict[str, Any] | Any | None = None) -> str | None:
    normalized_topic = normalize_text(topic)
    if "rag" in normalized_topic or "检索增强生成" in normalized_topic or "retrieval augmented generation" in normalized_topic:
        if any(marker in normalized_text for marker in ("image generation", "text to image", "vision", "diffusion")):
            if not any(marker in normalized_text for marker in ("llm", "language model", "question answering", "knowledge")):
                return "domain_conflict"
    if "大语言模型" in normalized_topic or "llm" in normalized_topic or "language model" in normalized_topic:
        published_at = getattr(item, "published_at", None) or (item.get("published_at") if isinstance(item, dict) else None)
        year_match = re.match(r"(\d{4})", str(published_at or ""))
        if year_match and int(year_match.group(1)) < 2018:
            if not any(marker in normalized_text for marker in ("llm", "language model", "large language model")):
                return "pre_llm_domain_conflict"
        if any(marker in normalized_text for marker in ("reinforcement learning", "deep reinforcement learning")):
            if not any(marker in normalized_text for marker in ("llm", "language model", "tool", "prompt")):
                return "domain_conflict"
    return None


def _is_case_study_evidence(item: dict[str, Any] | Any) -> bool:
    """判断来源是否提供真实落地案例，而非综述/背景介绍。"""
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    normalized_text = normalize_text(
        f"{getattr(item, 'title', None) or item.get('title', '')} "
        f"{getattr(item, 'snippet', None) or item.get('snippet', '')} "
        f"{getattr(item, 'url', None) or item.get('url', '')}"
    )
    negative_markers = ("survey", "review", "benchmark", "overview", "landscape", "trend")
    if any(marker in normalized_text for marker in negative_markers):
        return False

    positive_markers = (
        "case study",
        "customer story",
        "deployment",
        "production use",
        "in production",
        "production",
        "real world",
        "real-world",
        "use case",
        "application example",
    )
    if source_type == "github":
        return any(marker in normalized_text for marker in ("production", "application", "example", "project", "deployment"))
    return any(marker in normalized_text for marker in positive_markers)


def _aspect_support_specificity(item: dict[str, Any] | Any, task) -> float:
    normalized_text = normalize_text(
        f"{getattr(item, 'title', None) or item.get('title', '')} {getattr(item, 'snippet', None) or item.get('snippet', '')}"
    )
    text_tokens = set(tokenize_text(normalized_text))
    task_type = getattr(task, "task_type", "research")
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    aspect = (getattr(task, "expected_aspects", None) or [getattr(task, "title", "")])[0]
    semantic_terms = _aspect_semantic_terms(aspect, task_type)
    topic_terms = _topic_guard_terms(getattr(task, "query", ""))
    generic_terms = set(token.lower() for token in _topic_alias_terms(getattr(task, "query", "")))
    normalized_aspect = normalize_text(aspect)

    if "mcp" in normalize_text(getattr(task, "query", "")) or "model context protocol" in normalize_text(
        getattr(task, "query", "")
    ):
        semantic_terms = _dedupe_terms([*semantic_terms, "mcp", "model context protocol"])
        if "工具发现" in normalized_aspect:
            semantic_terms = _dedupe_terms([*semantic_terms, "tool discovery", "capability discovery", "tool registry"])
        if "权限" in normalized_aspect or "安全" in normalized_aspect:
            semantic_terms = _dedupe_terms([*semantic_terms, "security", "permission", "authorization", "access control", "oauth"])
        if "基本概念" in normalized_aspect:
            semantic_terms = _dedupe_terms([*semantic_terms, "protocol", "client", "server", "resource", "tool"])
        if "接入模式" in normalized_aspect or ("接入" in normalized_aspect and "模式" in normalized_aspect):
            semantic_terms = _dedupe_terms(
                [*semantic_terms, "integration pattern", "tool integration", "transport", "stdio", "sse", "streamable http"]
            )
        if "错误恢复" in normalized_aspect:
            semantic_terms = _dedupe_terms([*semantic_terms, "error handling", "retry", "fallback", "reconnect", "recovery"])

    critical_terms = [
        term
        for term in semantic_terms
        if normalize_text(term)
        and _is_specific_term(normalize_text(term))
        and normalize_text(term) not in generic_terms
        and normalize_text(term)
        not in {
            "rag",
            "agent",
            "llm",
            "language model",
            "retrieval augmented generation",
            "multi",
            "plan",
            "execute",
        }
    ]
    if not critical_terms:
        critical_terms = semantic_terms or list(getattr(task, "must_include_terms", []) or [])

    critical_score = _term_match_score(normalized_text, text_tokens, critical_terms)
    semantic_score = _term_match_score(normalized_text, text_tokens, semantic_terms or critical_terms)
    topic_score = _term_match_score(normalized_text, text_tokens, topic_terms) if topic_terms else 0.5
    critical_hit = 1.0 if critical_score > 0 else 0.0
    specificity = 0.55 * critical_hit + 0.25 * semantic_score + 0.20 * topic_score
    if task_type == "tutorial" and source_type == "github" and topic_score >= 0.5:
        specificity = max(specificity, 0.3)
    if task_type == "product":
        case_meta = _classify_case_study_item(item, task)
        if case_meta.get("case_study_evidence"):
            case_strength = float(case_meta.get("case_study_strength_score", 0.0) or 0.0)
            specificity = max(specificity, 0.34 + 0.46 * case_strength)
    return round(min(1.0, specificity), 3)


def _term_match_score(normalized_text: str, text_tokens: set[str], terms: list[str]) -> float:
    if not terms:
        return 0.0
    matched = 0
    for term in terms:
        candidate = normalize_text(term)
        if not candidate:
            continue
        if " " in candidate:
            term_tokens = set(tokenize_text(candidate))
            if candidate in normalized_text or (term_tokens and term_tokens.issubset(text_tokens)):
                matched += 1
        elif candidate in normalized_text or candidate in text_tokens:
            matched += 1
    return matched / max(len(terms), 1)


def _is_specific_term(term: str) -> bool:
    if not term:
        return False
    if not re.fullmatch(r"[a-z0-9\-\s+.\/]+", term):
        return True
    if any(marker in term for marker in ("-", " ", "/")):
        return True
    return len(term) >= 5


def _minimum_support_specificity(task, item: dict[str, Any] | Any) -> float:
    task_type = getattr(task, "task_type", "research")
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    aspect = (getattr(task, "expected_aspects", None) or [getattr(task, "title", "")])[0]
    threshold = 0.18 if task_type == "tutorial" else 0.24
    if source_type == "arxiv":
        threshold += 0.14
    elif source_type == "github":
        threshold += 0.06

    normalized_aspect = normalize_text(aspect)
    if any(
        marker in normalized_aspect
        for marker in (
            "langgraph",
            "crewai",
            "autogen",
            "faiss",
            "milvus",
            "chroma",
            "chunking",
            "embedding",
            "faithfulness",
            "relevance",
            "recall",
            "tool calling",
            "function calling",
        )
    ):
        threshold += 0.10
    if task_type == "product":
        case_study_evidence = False
        case_strength = 0.0
        if isinstance(item, dict):
            case_study_evidence = bool(item.get("case_study_evidence"))
            case_strength = float(item.get("case_study_strength_score", 0.0) or 0.0)
        else:
            metadata = getattr(item, "metadata", {}) or {}
            case_study_evidence = bool(metadata.get("case_study_evidence"))
            case_strength = float(metadata.get("case_study_strength_score", 0.0) or 0.0)
        if case_study_evidence and case_strength >= 0.65:
            threshold = min(threshold, 0.22 if source_type == "github" else 0.18)
    return round(min(threshold, 0.6), 3)


def _direct_support_threshold(task, item: dict[str, Any] | Any) -> float:
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    threshold = 0.52 if source_type == "arxiv" else 0.42
    aspect = (getattr(task, "expected_aspects", None) or [getattr(task, "title", "")])[0]
    normalized_aspect = normalize_text(aspect)
    if any(marker in normalized_aspect for marker in ("faiss", "milvus", "chroma", "langgraph", "crewai", "autogen")):
        threshold += 0.06
    return round(min(threshold, 0.7), 3)


def _topic_guard_override_threshold(task, item: dict[str, Any] | Any) -> float:
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    trust_tier = _trust_tier(item)
    if source_type == "arxiv":
        threshold = 0.55
    elif source_type == "github":
        threshold = 0.45
    elif trust_tier >= 4:
        threshold = 0.45
    else:
        threshold = 0.75
    task_type = getattr(task, "task_type", "research")
    if task_type == "tutorial":
        threshold = 0.4
    return threshold


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(b), 1)


def evaluate_quality_gate(
    *,
    tasks,
    task_summaries: list[str],
    sources,
    loop_count: int,
    max_loops: int,
    research_topic: str | None = None,
) -> dict[str, Any]:
    """根据确定性规则评估 benchmark 质量门控。"""
    missing_aspects: list[str] = []
    fail_reasons: list[str] = []
    for task, summary in zip(tasks, task_summaries):
        for aspect in task.expected_aspects:
            if not _strict_aspect_hit(summary, aspect):
                missing_aspects.append(aspect)

    selected_sources = [source for source in sources if getattr(source, "selected", True)]
    high_trust_sources = [source for source in selected_sources if getattr(source, "trust_tier", 3) >= 4]
    case_study_evidence_count = sum(
        1 for source in selected_sources if bool(getattr(source, "metadata", {}).get("case_study_evidence"))
    )
    high_trust_case_study_count = sum(
        1
        for source in selected_sources
        if bool(getattr(source, "metadata", {}).get("case_study_evidence"))
        and getattr(source, "trust_tier", 3) >= 4
    )
    for task in tasks:
        for aspect in task.expected_aspects:
            if not is_case_study_aspect(aspect):
                continue
            task_sources = [source for source in selected_sources if getattr(source, "task_title", "") == task.title]
            task_case_study_sources = [
                source for source in task_sources if bool(getattr(source, "metadata", {}).get("case_study_evidence"))
            ]
            task_high_trust_case_studies = [
                source
                for source in task_case_study_sources
                if getattr(source, "trust_tier", 3) >= 4
                and bool(getattr(source, "metadata", {}).get("matches_topic_family"))
                and float(getattr(source, "metadata", {}).get("case_study_strength_score", 0.0) or 0.0) >= 0.65
            ]
            if task_high_trust_case_studies:
                continue
            if aspect not in missing_aspects:
                missing_aspects.append(aspect)
            if task_case_study_sources:
                if any(not bool(getattr(source, "metadata", {}).get("matches_topic_family")) for source in task_case_study_sources):
                    fail_reasons.append("案例与主题相关性不足")
                elif any(
                    float(getattr(source, "metadata", {}).get("case_study_strength_score", 0.0) or 0.0) >= 0.45
                    for source in task_case_study_sources
                ):
                    fail_reasons.append("缺少真实部署或客户案例信号")
                else:
                    fail_reasons.append("缺少官方或高可信案例来源")
            elif task_sources:
                fail_reasons.append("缺少官方或高可信案例来源")
            else:
                fail_reasons.append("缺少真实案例证据")

    high_trust_ratio = len(high_trust_sources) / len(selected_sources) if selected_sources else 0.0
    if high_trust_ratio < 0.4:
        for task in tasks:
            for aspect in task.expected_aspects:
                if aspect not in missing_aspects:
                    missing_aspects.append(aspect)
        fail_reasons.append("高可信来源占比不足")

    passed = bool(selected_sources) and not missing_aspects and high_trust_ratio >= 0.4
    if passed:
        return {
            "passed": True,
            "quality_gate_status": "passed",
            "missing_aspects": [],
            "follow_up_queries": [],
            "high_trust_source_ratio": round(high_trust_ratio, 3),
            "quality_gate_fail_reason": "",
            "case_study_evidence_count": case_study_evidence_count,
            "high_trust_case_study_count": high_trust_case_study_count,
        }

    follow_up_queries = []
    topic_text = research_topic or (getattr(tasks[0], "query", "") if tasks else "")
    for aspect in missing_aspects[:2]:
        matched_task = next((task for task in tasks if aspect in getattr(task, "expected_aspects", [])), None)
        follow_up_queries.extend(_build_follow_up_queries(topic_text, aspect, [matched_task] if matched_task else tasks))

    if loop_count + 1 >= max_loops:
        return {
            "passed": False,
            "quality_gate_status": "failed",
            "missing_aspects": missing_aspects,
            "follow_up_queries": follow_up_queries,
            "high_trust_source_ratio": round(high_trust_ratio, 3),
            "quality_gate_fail_reason": "；".join(dict.fromkeys(fail_reasons)) or "质量门控未通过",
            "case_study_evidence_count": case_study_evidence_count,
            "high_trust_case_study_count": high_trust_case_study_count,
        }

    return {
        "passed": False,
        "quality_gate_status": "needs_more_research",
        "missing_aspects": missing_aspects,
        "follow_up_queries": follow_up_queries,
        "high_trust_source_ratio": round(high_trust_ratio, 3),
        "quality_gate_fail_reason": "；".join(dict.fromkeys(fail_reasons)) or "需要补充研究",
        "case_study_evidence_count": case_study_evidence_count,
        "high_trust_case_study_count": high_trust_case_study_count,
    }


def _strict_aspect_hit(text: str, aspect: str) -> bool:
    """质量门控使用更严格的方面命中判定。"""
    body_only = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    normalized = normalize_text(body_only)
    keywords = extract_aspect_keywords(aspect)
    ascii_keywords = [keyword for keyword in keywords if re.fullmatch(r"[a-z0-9]+", keyword)]
    if len(ascii_keywords) >= 2:
        return all(keyword in normalized for keyword in ascii_keywords)
    matched = [keyword for keyword in keywords if keyword in normalized]
    threshold = 1 if len(keywords) <= 2 else max(2, int(len(keywords) * 0.6 + 0.999))
    return len(matched) >= threshold


def _build_follow_up_queries(topic_text: str, aspect: str, tasks) -> list[str]:
    task_type = getattr(tasks[0], "task_type", "research") if tasks else "research"
    aspect_query = _compact_query([topic_text, aspect, *extract_aspect_keywords(aspect)])
    if task_type == "tutorial":
        return [f"{aspect_query} official documentation github install troubleshooting".strip()]
    if task_type == "product":
        family_text = _compact_query(_case_study_topic_family_terms(topic_text))
        queries = [
            f"{aspect_query} {family_text} official case study customer story deployment production use".strip(),
            f"{aspect_query} {family_text} official product blog customer story".strip(),
        ]
        for domain in _case_study_domains_for_topic(topic_text)[:4]:
            queries.append(
                f"{aspect_query} site:{domain} {family_text} case study customer story deployment".strip()
            )
        return _dedupe_terms(queries)
    return [f"{aspect_query} official docs github arxiv survey".strip()]


def build_benchmark_report(
    *,
    topic: str,
    tasks,
    task_summaries: list[str],
    sources,
    evidence_notes=None,
) -> str:
    """构造稳定的 benchmark 报告。"""
    global_context = _build_global_context(sources)
    aspect_overview = "；".join(
        aspect
        for task in tasks
        for aspect in getattr(task, "expected_aspects", [])[:1]
    )
    sections = [
        f"# {topic}",
        "",
        "## 概述",
        "",
        _append_citation_suffix(
            f"本报告围绕“{topic}”按方面展开，重点覆盖：{aspect_overview}。正文优先依据高可信来源给出结论。",
            _pick_citation_ids(
                global_context["direct_high_trust_ids"] or global_context["high_trust_ids"] or global_context["selected_ids"],
                min_count=1,
                max_count=2,
            ),
        ),
        "",
    ]

    for index, (task, summary) in enumerate(zip(tasks, task_summaries), start=1):
        task_context = _build_task_context(task, sources, evidence_notes or [])
        sections.append(f"## {index}. {task.title}")
        sections.append("")
        sections.append(_lint_task_summary(summary.strip(), task_context))
        sections.append("")

    sections.append("## 总结")
    sections.append("")
    sections.append(
        _append_citation_suffix(
            f"综合来看，“{topic}”的核心判断优先依据高可信来源整理；证据不足的部分已明确降级为保守结论。",
            _pick_citation_ids(
                global_context["direct_high_trust_ids"] or global_context["high_trust_ids"] or global_context["selected_ids"],
                min_count=1,
                max_count=3,
            ),
        )
    )
    sections.append("")

    used_ids = sorted({int(match) for match in re.findall(r"\[(\d+)\]", "\n".join(sections))})
    sections.append("## 参考来源")
    sections.append("")
    for source in sources:
        if source.citation_id in used_ids:
            sections.append(f"[{source.citation_id}] {source.title} - {source.url}")

    return "\n".join(sections).strip() + "\n"


def _lint_task_summary(summary: str, task_context: dict[str, Any]) -> str:
    """为 benchmark task summary 补齐可信度结构和引用。"""
    normalized_summary = _strip_leading_heading(summary)
    if "### " not in normalized_summary:
        normalized_summary = _wrap_unstructured_summary(normalized_summary, task_context)

    paragraphs = normalized_summary.split("\n\n")
    current_heading = ""
    linted: list[str] = []

    for paragraph in paragraphs:
        block = paragraph.strip()
        if not block:
            continue
        if block.startswith("#"):
            current_heading = block
            linted.append(block)
            continue

        if "### 核心结论" in current_heading:
            if task_context["direct_high_trust_ids"]:
                block = _ensure_high_trust_citations(block, task_context["direct_high_trust_ids"])
            elif task_context["high_trust_ids"]:
                block = _ensure_weak_language(block)
                block = _ensure_citations(
                    block,
                    task_context["high_trust_ids"],
                    min_count=1,
                    max_count=2,
                )
            else:
                block = _ensure_weak_language(block)
                block = _ensure_citations(
                    block,
                    task_context["provenance_ids"] or task_context["supplementary_ids"] or task_context["selected_ids"],
                    min_count=1,
                    max_count=3,
                )
        elif "### 补充观察" in current_heading:
            block = _ensure_citations(
                block,
                task_context["supplementary_ids"] or task_context["selected_ids"] or task_context["provenance_ids"],
                min_count=1,
                max_count=3,
            )
        elif "### 证据限制" in current_heading:
            block = _ensure_weak_language(block)
            block = _ensure_citations(
                block,
                task_context["provenance_ids"] or task_context["selected_ids"] or task_context["high_trust_ids"],
                min_count=1,
                max_count=3,
            )
        else:
            block = _ensure_citations(
                block,
                task_context["direct_high_trust_ids"] or task_context["high_trust_ids"] or task_context["selected_ids"] or task_context["provenance_ids"],
                min_count=1,
                max_count=2,
            )

        linted.append(block)

    return "\n\n".join(linted).strip()


def _wrap_unstructured_summary(summary: str, task_context: dict[str, Any]) -> str:
    """把未结构化的 summary 包成可信度优先的固定三段式。"""
    paragraphs = [
        block.strip()
        for block in summary.split("\n\n")
        if block.strip() and not block.strip().startswith("#")
    ]
    first_paragraph = paragraphs[0] if paragraphs else "当前尚未形成可验证的章节结论。"
    extra_paragraphs = paragraphs[1:]

    if task_context["high_trust_ids"]:
        core_claim = first_paragraph
    else:
        core_claim = _ensure_weak_language(first_paragraph)

    if extra_paragraphs:
        supplementary = " ".join(extra_paragraphs)
    elif task_context["supplementary_ids"]:
        supplementary = "补充资料提供了额外线索，但其可信度弱于核心证据，应谨慎采信。"
    else:
        supplementary = "当前未发现与核心判断明显冲突的低可信补充资料，本节以高可信来源为主。"

    if task_context["high_trust_ids"]:
        limitation = "当前核心判断主要依赖少量高可信来源，仍需更多独立来源或官方文档交叉验证。"
    else:
        limitation = "当前仅有中低可信公开资料，结论应视为阶段性判断，仍需官方文档或论文进一步验证。"

    return (
        "### 核心结论\n\n"
        f"{core_claim}\n\n"
        "### 补充观察\n\n"
        f"{supplementary}\n\n"
        "### 证据限制\n\n"
        f"{limitation}"
    )


def _build_global_context(sources) -> dict[str, list[int]]:
    selected_records = _sort_records([source for source in sources if getattr(source, "selected", True)])
    high_trust_records = [source for source in selected_records if getattr(source, "trust_tier", 3) >= 4]
    direct_high_trust_records = [source for source in high_trust_records if _record_support_specificity(source) >= 0.45]
    return {
        "selected_ids": [source.citation_id for source in selected_records],
        "high_trust_ids": [source.citation_id for source in high_trust_records],
        "direct_high_trust_ids": [source.citation_id for source in direct_high_trust_records],
    }


def _build_task_context(task, sources, evidence_notes) -> dict[str, list[int]]:
    source_index = {source.citation_id: source for source in sources}
    note = _find_task_note(task, evidence_notes)
    selected_ids = _unique_ints(
        _note_field(note, "selected_source_ids")
        or [
            source.citation_id
            for source in sources
            if source.task_title == task.title and getattr(source, "selected", True)
        ]
    )
    provenance_ids = _unique_ints(
        _note_field(note, "source_ids")
        or [source.citation_id for source in sources if source.task_title == task.title]
    )
    selected_records = _sort_records([source_index[citation_id] for citation_id in selected_ids if citation_id in source_index])
    high_trust_ids = [source.citation_id for source in selected_records if getattr(source, "trust_tier", 3) >= 4]
    direct_high_trust_ids = [
        source.citation_id
        for source in selected_records
        if getattr(source, "trust_tier", 3) >= 4 and _record_support_specificity(source) >= 0.45
    ]
    supplementary_ids = [source.citation_id for source in selected_records if getattr(source, "trust_tier", 3) < 4]

    return {
        "selected_ids": selected_ids,
        "high_trust_ids": high_trust_ids,
        "direct_high_trust_ids": direct_high_trust_ids,
        "supplementary_ids": supplementary_ids,
        "provenance_ids": provenance_ids or selected_ids,
    }


def _find_task_note(task, evidence_notes):
    for note in evidence_notes:
        if _note_field(note, "task_id") == getattr(task, "id", None):
            return note
        if _note_field(note, "task_title") == getattr(task, "title", ""):
            return note
    return None


def _note_field(note, field: str):
    if note is None:
        return None
    if isinstance(note, dict):
        return note.get(field)
    return getattr(note, field, None)


def _sort_records(records) -> list[Any]:
    return sorted(
        records,
        key=lambda source: (-int(getattr(source, "trust_tier", 3)), int(getattr(source, "citation_id", 0))),
    )


def _strip_leading_heading(summary: str) -> str:
    lines = summary.splitlines()
    while lines and re.match(r"^#{1,2}\s+", lines[0].strip()):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _ensure_high_trust_citations(paragraph: str, high_trust_ids: list[int]) -> str:
    cited_ids = _extract_citation_ids(paragraph)
    if any(citation_id in high_trust_ids for citation_id in cited_ids):
        return paragraph
    return _append_citation_suffix(
        paragraph,
        _pick_citation_ids(high_trust_ids, min_count=1, max_count=3, exclude_ids=cited_ids),
    )


def _ensure_citations(paragraph: str, candidate_ids: list[int], *, min_count: int, max_count: int) -> str:
    cited_ids = _extract_citation_ids(paragraph)
    if cited_ids:
        return paragraph
    return _append_citation_suffix(
        paragraph,
        _pick_citation_ids(candidate_ids, min_count=min_count, max_count=max_count),
    )


def _ensure_weak_language(paragraph: str) -> str:
    if any(marker in paragraph for marker in _WEAK_EVIDENCE_MARKERS):
        return paragraph
    citation_ids = _extract_citation_ids(paragraph)
    stripped = re.sub(r"\s*\[\d+\]", "", paragraph).rstrip("。.!！?？ ")
    weakened = f"{stripped}，但证据仍有限，需进一步验证。"
    return _append_citation_suffix(weakened, citation_ids)


def _pick_citation_ids(
    candidate_ids: list[int],
    *,
    min_count: int,
    max_count: int,
    exclude_ids: list[int] | None = None,
) -> list[int]:
    exclude = set(exclude_ids or [])
    picked = [citation_id for citation_id in _unique_ints(candidate_ids) if citation_id not in exclude]
    if not picked:
        return []
    count = min(max_count, len(picked))
    if count < min_count:
        count = len(picked)
    return picked[:count]


def _append_citation_suffix(paragraph: str, citation_ids: list[int]) -> str:
    if not citation_ids:
        return paragraph
    suffix = "".join(f"[{citation_id}]" for citation_id in citation_ids)
    return f"{paragraph.rstrip()} {suffix}".rstrip()


def _extract_citation_ids(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"\[(\d+)\]", text)]


def _unique_ints(values) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values or []:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _record_support_specificity(source) -> float:
    metadata = getattr(source, "metadata", None) or {}
    value = metadata.get("support_specificity")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
