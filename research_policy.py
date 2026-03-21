"""Benchmark profile 下的确定性研究策略。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


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


def should_use_source(task_type: str, source_name: str) -> bool:
    """判断任务类型是否启用某种来源。"""
    return source_name in preferred_sources_for_task(task_type)


def build_benchmark_tasks(topic_spec) -> list[Any]:
    """根据 TopicSpec 生成稳定的 benchmark 任务。"""
    from workflows.states import TaskItem

    task_type = infer_task_type(topic_spec.topic)
    preferred_sources = preferred_sources_for_task(task_type)
    tasks: list[TaskItem] = []

    for index, aspect in enumerate(topic_spec.expected_aspects or [topic_spec.topic], start=1):
        query = _build_query(topic_spec.topic, aspect, task_type)
        tasks.append(
            TaskItem(
                id=index,
                title=_task_title_from_aspect(aspect),
                intent=f"重点覆盖方面：{aspect}",
                query=query,
                task_type=task_type,
                expected_aspects=[aspect],
                preferred_sources=preferred_sources,
                must_include_terms=_aspect_required_terms(aspect, task_type),
                avoid_terms=["arxiv"] if task_type == "tutorial" else [],
            )
        )
    return tasks


def build_source_query(task, source_name: str) -> str:
    """为不同来源构造更稳健的查询语句。"""
    aspect = (task.expected_aspects or [task.title])[0]
    task_type = getattr(task, "task_type", infer_task_type(task.query))
    base_terms = [task.query]
    aspect_terms = _aspect_boost_terms(aspect, task_type)

    if source_name == "github":
        base_terms.extend(["github", "repository", "official"])
    elif source_name == "arxiv":
        base_terms.extend(["paper", "survey", "benchmark"])
    else:
        base_terms.extend(["official documentation"])

    if task_type == "product":
        base_terms.extend(["case study", "production", "enterprise application"])
    if task_type == "tutorial":
        base_terms.extend(["install", "setup", "quick start"])

    if source_name == "arxiv" and task_type in {"tutorial", "product", "organization"}:
        return task.query

    return _compact_query([*base_terms, *aspect_terms])


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
    if task_type == "comparison":
        return f"{base} comparison benchmark differences"
    return _compact_query([base, *_aspect_boost_terms(aspect, task_type)])


def _aspect_boost_terms(aspect: str, task_type: str) -> list[str]:
    normalized = normalize_text(aspect)
    boosts: list[str] = []
    if "memory" in normalized or "记忆" in normalized:
        boosts.extend(["memory", "long-term memory", "episodic memory"])
    if "tool calling" in normalized or "function calling" in normalized or "工具" in normalized:
        boosts.extend(["tool calling", "function calling"])
    if "框架" in normalized or "langgraph" in normalized or "crewai" in normalized or "autogen" in normalized:
        boosts.extend(["LangGraph", "CrewAI", "AutoGen", "comparison"])
    if "应用案例" in normalized or normalized.endswith("案例"):
        boosts.extend(["case study", "application", "enterprise"])
    if "评估指标" in normalized or any(token in normalized for token in {"faithfulness", "relevance", "recall"}):
        boosts.extend(["evaluation", "faithfulness", "relevance", "recall"])
    if "chunking" in normalized or "embedding" in normalized:
        boosts.extend(["chunking", "embedding", "retrieval"])
    if task_type == "research" and not boosts:
        boosts.extend(["survey", "official docs"])
    return boosts


def _aspect_required_terms(aspect: str, task_type: str) -> list[str]:
    normalized = normalize_text(aspect)
    terms = list(tokenize_text(aspect)[:4])
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
    return _dedupe_terms(terms)


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
    query_tokens = set(tokenize_text(task.query))
    task_tokens = set(tokenize_text(task.title)) | set(tokenize_text(" ".join(task.expected_aspects)))
    stats = {"off_topic_reject_count": 0, "duplicate_reject_count": 0}
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    required_tokens = set(getattr(task, "must_include_terms", []) or [])
    avoid_tokens = set(getattr(task, "avoid_terms", []) or [])

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

        text_tokens = set(tokenize_text(f"{item.get('title', '')} {item.get('snippet', '')}"))
        if required_tokens and not (text_tokens & required_tokens) and _trust_tier(item) < 4:
            item["rejection_reason"] = "missing_required_terms"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue
        if avoid_tokens and (text_tokens & avoid_tokens):
            item["rejection_reason"] = "contains_avoid_terms"
            rejected.append(item)
            stats["off_topic_reject_count"] += 1
            continue

        score = _score_source_item(item, query_tokens=query_tokens, task_tokens=task_tokens, anchor_tokens=anchor_tokens)
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
) -> float:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    text = f"{title} {snippet}"
    text_tokens = set(tokenize_text(text))
    trust = _trust_tier(item) / 5
    overlap = _overlap_score(text_tokens, query_tokens | task_tokens)
    anchor_score = _overlap_score(text_tokens, anchor_tokens) if anchor_tokens else 0.5
    return 0.45 * overlap + 0.35 * trust + 0.20 * anchor_score


def _trust_tier(item: dict[str, Any] | Any) -> int:
    source_type = getattr(item, "source_type", None) or item.get("source_type", "web")
    url = getattr(item, "url", None) or item.get("url", "")

    if source_type == "github":
        return 5
    if source_type == "arxiv":
        return 4
    if "github.com" in url or "docs." in url:
        return 4
    if "reddit.com" in url or "facebook.com" in url:
        return 1
    return 3


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
    for task, summary in zip(tasks, task_summaries):
        for aspect in task.expected_aspects:
            if not _strict_aspect_hit(summary, aspect):
                missing_aspects.append(aspect)

    selected_sources = [source for source in sources if getattr(source, "selected", True)]
    high_trust_sources = [source for source in selected_sources if getattr(source, "trust_tier", 3) >= 4]
    high_trust_ratio = len(high_trust_sources) / len(selected_sources) if selected_sources else 0.0
    if high_trust_ratio < 0.4:
        for task in tasks:
            for aspect in task.expected_aspects:
                if aspect not in missing_aspects:
                    missing_aspects.append(aspect)

    passed = bool(selected_sources) and not missing_aspects and high_trust_ratio >= 0.4
    if passed:
        return {
            "passed": True,
            "quality_gate_status": "passed",
            "missing_aspects": [],
            "follow_up_queries": [],
            "high_trust_source_ratio": round(high_trust_ratio, 3),
        }

    follow_up_queries = []
    topic_text = research_topic or (getattr(tasks[0], "query", "") if tasks else "")
    for aspect in missing_aspects[:2]:
        follow_up_queries.extend(_build_follow_up_queries(topic_text, aspect, tasks))

    if loop_count + 1 >= max_loops:
        return {
            "passed": False,
            "quality_gate_status": "failed",
            "missing_aspects": missing_aspects,
            "follow_up_queries": follow_up_queries,
            "high_trust_source_ratio": round(high_trust_ratio, 3),
        }

    return {
        "passed": False,
        "quality_gate_status": "needs_more_research",
        "missing_aspects": missing_aspects,
        "follow_up_queries": follow_up_queries,
        "high_trust_source_ratio": round(high_trust_ratio, 3),
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
        return [f"{aspect_query} official case study github documentation".strip()]
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
            _pick_citation_ids(global_context["high_trust_ids"] or global_context["selected_ids"], min_count=1, max_count=2),
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
            _pick_citation_ids(global_context["high_trust_ids"] or global_context["selected_ids"], min_count=1, max_count=3),
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
            if task_context["high_trust_ids"]:
                block = _ensure_high_trust_citations(block, task_context["high_trust_ids"])
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
                task_context["high_trust_ids"] or task_context["selected_ids"] or task_context["provenance_ids"],
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
    return {
        "selected_ids": [source.citation_id for source in selected_records],
        "high_trust_ids": [source.citation_id for source in high_trust_records],
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
    supplementary_ids = [source.citation_id for source in selected_records if getattr(source, "trust_tier", 3) < 4]

    return {
        "selected_ids": selected_ids,
        "high_trust_ids": high_trust_ids,
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
