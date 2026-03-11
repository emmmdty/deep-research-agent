"""Researcher Agent——执行多源搜索并生成结构化证据。"""

from __future__ import annotations

from loguru import logger

from configs.settings import get_settings
from llm.provider import get_llm
from prompts.templates import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT
from tools.arxiv_search import search_arxiv_papers
from tools.github_search import search_github_repositories
from tools.web_search import search_web
from workflows.states import EvidenceNote, SourceRecord, TaskItem


def researcher_node(state: dict) -> dict:
    """LangGraph 节点：对每个未完成的子任务执行搜索和总结。"""
    settings = get_settings()
    tasks: list[TaskItem] = state.get("tasks", [])
    research_topic = state["research_topic"]
    task_summaries: list[str] = list(state.get("task_summaries", []))
    sources_gathered: list[SourceRecord] = list(state.get("sources_gathered", []))
    search_results: list[str] = list(state.get("search_results", []))
    evidence_notes: list[EvidenceNote] = list(state.get("evidence_notes", []))

    critic_feedback = state.get("critic_feedback")
    follow_up_queries: list[str] = []
    if critic_feedback and hasattr(critic_feedback, "follow_up_queries"):
        follow_up_queries = critic_feedback.follow_up_queries

    llm = get_llm()

    if follow_up_queries:
        logger.info("🔄 Researcher 执行补充搜索: {} 个查询", len(follow_up_queries))
        for query in follow_up_queries:
            _execute_single_search(
                query=query,
                task_id=None,
                task_title="补充研究",
                task_intent="填充知识空白",
                research_topic=research_topic,
                llm=llm,
                enabled_sources=settings.enabled_sources,
                max_results=settings.max_search_results,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                search_results=search_results,
                evidence_notes=evidence_notes,
            )
    else:
        logger.info("🔍 Researcher 开始执行 {} 个子任务", len(tasks))
        for task in tasks:
            if task.status == "completed":
                continue

            _execute_single_search(
                query=task.query,
                task_id=task.id,
                task_title=task.title,
                task_intent=task.intent,
                research_topic=research_topic,
                llm=llm,
                enabled_sources=settings.enabled_sources,
                max_results=settings.max_search_results,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                search_results=search_results,
                evidence_notes=evidence_notes,
            )
            task.status = "completed"
            if task_summaries:
                task.summary = task_summaries[-1]
            if evidence_notes:
                latest_note = evidence_notes[-1]
                task.sources = ", ".join(f"[{item}]" for item in latest_note.source_ids)

    logger.info(
        "🔍 Researcher 执行完成: 总结数={}, 来源数={}",
        len(task_summaries),
        len(sources_gathered),
    )

    return {
        "tasks": tasks,
        "task_summaries": task_summaries,
        "sources_gathered": sources_gathered,
        "search_results": search_results,
        "evidence_notes": evidence_notes,
        "status": "researched",
    }


def _execute_single_search(
    *,
    query: str,
    task_id: int | None,
    task_title: str,
    task_intent: str,
    research_topic: str,
    llm,
    enabled_sources: list[str],
    max_results: int,
    task_summaries: list[str],
    sources_gathered: list[SourceRecord],
    search_results: list[str],
    evidence_notes: list[EvidenceNote],
) -> None:
    """执行单个搜索 + 总结流程。"""
    logger.info("  🔎 搜索: '{}'", query)

    results = _collect_results(
        query=query,
        task_title=task_title,
        enabled_sources=enabled_sources,
        max_results=max_results,
        start_index=len(sources_gathered) + 1,
    )
    sources_gathered.extend(results)

    search_context = _format_context(results)
    search_results.append(search_context)

    if not results:
        logger.warning("  ⚠️ 搜索无结果: '{}'", query)
        empty_summary = f"## {task_title}\n\n暂无可用信息。\n"
        task_summaries.append(empty_summary)
        evidence_notes.append(
            EvidenceNote(
                task_id=task_id,
                task_title=task_title,
                query=query,
                summary=empty_summary,
                source_ids=[],
            )
        )
        return

    user_prompt = SUMMARIZER_USER_PROMPT.format(
        research_topic=research_topic,
        task_title=task_title,
        task_intent=task_intent,
        task_query=query,
        context=search_context,
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    summary = response.content

    from llm.clean import clean_llm_output

    summary = clean_llm_output(summary)
    task_summaries.append(summary)
    evidence_notes.append(
        EvidenceNote(
            task_id=task_id,
            task_title=task_title,
            query=query,
            summary=summary,
            source_ids=[record.citation_id for record in results],
        )
    )
    logger.info("  ✅ 总结完成: '{}'", task_title)


def _collect_results(
    *,
    query: str,
    task_title: str,
    enabled_sources: list[str],
    max_results: int,
    start_index: int,
) -> list[SourceRecord]:
    """采集多源搜索结果。"""
    collectors = {
        "web": search_web,
        "github": search_github_repositories,
        "arxiv": search_arxiv_papers,
    }

    results: list[SourceRecord] = []
    citation_id = start_index
    for source_name in enabled_sources:
        collector = collectors.get(source_name)
        if collector is None:
            continue

        raw_items = collector(query, max_results=max_results)
        for item in raw_items:
            results.append(
                SourceRecord(
                    citation_id=citation_id,
                    source_type=item.get("source_type", source_name),
                    query=query,
                    title=item.get("title", "无标题"),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    task_title=task_title,
                    published_at=item.get("published_at"),
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key
                        not in {"index", "source_type", "title", "url", "snippet", "published_at"}
                    },
                )
            )
            citation_id += 1
    return results


def _format_context(records: list[SourceRecord]) -> str:
    """将结构化来源格式化为总结上下文。"""
    if not records:
        return "搜索未返回结果。"

    parts = []
    for record in records:
        extra_bits = []
        if record.metadata.get("backend"):
            extra_bits.append(f"后端: {record.metadata['backend']}")
        if record.metadata.get("language"):
            extra_bits.append(f"语言: {record.metadata['language']}")
        if record.metadata.get("stars") is not None:
            extra_bits.append(f"Stars: {record.metadata['stars']}")
        if record.metadata.get("authors"):
            extra_bits.append(f"作者: {record.metadata['authors']}")

        extra_line = f"\n附加信息: {' | '.join(extra_bits)}" if extra_bits else ""
        parts.append(
            f"[{record.citation_id}] ({record.source_type}) {record.title}\n"
            f"URL: {record.url}\n"
            f"摘要: {record.snippet}{extra_line}\n"
        )
    return "\n".join(parts)
