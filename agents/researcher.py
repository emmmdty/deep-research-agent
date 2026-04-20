"""Researcher Agent——执行多源搜索并生成结构化证据。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger

from capabilities.mcp import invoke_mcp_capability
from capabilities.registry import build_capability_registry
from connectors.files import LocalFileIngestor
from connectors.legacy import LegacyConnectorAdapter
from connectors.models import ConnectorCandidate, ConnectorHealthRecord
from connectors.registry import ConnectorRegistry
from connectors.snapshot_store import SnapshotInput, SnapshotStore
from configs.settings import get_settings
from llm.provider import get_llm
from policies.budget_guardrails import BudgetGuard, BudgetUsage
from policies.source_policy import load_source_policy
from prompts.templates import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT
from research_policy import (
    aspect_hits_in_text,
    build_source_queries,
    extract_aspect_keywords,
    infer_task_type,
    is_case_study_aspect,
    select_sources_for_task,
    should_use_source,
)
from tools.arxiv_search import search_arxiv_papers
from tools.github_search import search_github_repositories
from tools.web_scraper import web_scraper_tool
from tools.web_search import search_web
from workflows.states import (
    EvidenceNote,
    RunMetrics,
    SourceRecord,
    TaskItem,
    ToolCapability,
    ToolInvocationRecord,
)


def researcher_node(state: dict) -> dict:
    """LangGraph 节点：对每个未完成的子任务执行搜索和总结。"""
    patch, _has_more_work = collect_research_step(state, max_units=None)
    return patch


def _fetch_web_candidate(url: str) -> dict[str, str]:
    """默认网页抓取；测试里的 example.com 走 snippet 回退。"""
    if "example.com" in url:
        return {"text": "", "mime_type": "text/html"}
    return {"text": web_scraper_tool.invoke({"url": url}), "mime_type": "text/html"}


def _build_phase3_connector_registry(_settings) -> ConnectorRegistry:
    """基于 researcher 模块级 search/fetch 函数构造 registry，便于测试 monkeypatch。"""
    return ConnectorRegistry(
        {
            "open_web": LegacyConnectorAdapter(source_name="web", search_fn=search_web, fetch_fn=_fetch_web_candidate),
            "github": LegacyConnectorAdapter(source_name="github", search_fn=search_github_repositories),
            "arxiv": LegacyConnectorAdapter(source_name="arxiv", search_fn=search_arxiv_papers),
            "files": LocalFileIngestor(),
        }
    )


def collect_research_step(
    state: dict,
    *,
    max_units: int | None = 1,
) -> tuple[dict, bool]:
    """执行 phase2 所需的单步 collecting。

    当 `max_units=1` 时，只处理一个 pending task 或一条 follow-up query；
    当 `max_units=None` 时，保留 legacy researcher 的整段执行行为。
    """
    settings = get_settings()
    registry = build_capability_registry(settings)
    tasks: list[TaskItem] = [
        task if isinstance(task, TaskItem) else TaskItem.model_validate(task)
        for task in state.get("tasks", [])
    ]
    research_topic = state["research_topic"]
    research_profile = state.get("research_profile", "default")
    ablation_variant = state.get("ablation_variant")
    file_inputs: list[str] = list(state.get("file_inputs", []))
    job_workspace_dir = str(state.get("job_workspace_dir") or getattr(settings, "workspace_dir", "workspace"))
    task_summaries: list[str] = list(state.get("task_summaries", []))
    sources_gathered: list[SourceRecord] = [
        source if isinstance(source, SourceRecord) else SourceRecord.model_validate(source)
        for source in state.get("sources_gathered", [])
    ]
    source_snapshots: list[dict[str, Any]] = list(state.get("source_snapshots", []))
    search_results: list[str] = list(state.get("search_results", []))
    evidence_notes: list[EvidenceNote] = [
        note if isinstance(note, EvidenceNote) else EvidenceNote.model_validate(note)
        for note in state.get("evidence_notes", [])
    ]
    available_capabilities: list[ToolCapability] = _filter_capabilities_for_variant(
        registry.list_all(),
        ablation_variant=ablation_variant,
    )
    capability_plan: dict[str, list[str]] = dict(state.get("capability_plan", {}))
    tool_invocations: list[ToolInvocationRecord] = [
        invocation
        if isinstance(invocation, ToolInvocationRecord)
        else ToolInvocationRecord.model_validate(invocation)
        for invocation in state.get("tool_invocations", [])
    ]
    coverage_status: dict[str, bool] = dict(state.get("coverage_status", {}))
    connector_health: dict[str, Any] = dict(state.get("connector_health", {}))
    run_metrics = state.get("run_metrics")
    if not isinstance(run_metrics, RunMetrics):
        run_metrics = RunMetrics.model_validate(run_metrics or {})

    critic_feedback = state.get("critic_feedback")
    follow_up_queries: list[str] = []
    failure_context: dict[str, Any] = {}
    if critic_feedback and hasattr(critic_feedback, "follow_up_queries"):
        follow_up_queries = critic_feedback.follow_up_queries
        failure_context = {
            "quality_gate_status": getattr(run_metrics, "quality_gate_status", ""),
            "gaps": list(getattr(critic_feedback, "gaps", [])),
        }

    llm = None
    if research_profile == "benchmark":
        try:
            llm = get_llm()
        except Exception as exc:  # pragma: no cover - 集成场景更常见
            logger.warning("⚠️ Benchmark profile 无法初始化 LLM，使用确定性总结回退: {}", exc)
    else:
        llm = get_llm()

    units_processed = 0
    if follow_up_queries:
        logger.info("🔄 Researcher 执行补充搜索: {} 个查询", len(follow_up_queries))
        remaining_follow_up_queries = list(follow_up_queries)
        for query in list(follow_up_queries):
            if max_units is not None and units_processed >= max_units:
                break
            target_task = _match_follow_up_task(query, tasks)
            _execute_single_search(
                query=query,
                task=target_task,
                task_id=target_task.id if target_task else None,
                task_title=target_task.title if target_task else "补充研究",
                task_intent=target_task.intent if target_task else "填充知识空白",
                research_topic=research_topic,
                research_profile=research_profile,
                llm=llm,
                enabled_sources=settings.enabled_sources,
                max_results=settings.max_search_results,
                per_source_max_results=settings.per_source_max_results,
                per_task_selected_sources=settings.per_task_selected_sources,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                source_snapshots=source_snapshots,
                search_results=search_results,
                evidence_notes=evidence_notes,
                capability_plan=capability_plan,
                tool_invocations=tool_invocations,
                coverage_status=coverage_status,
                connector_health=connector_health,
                run_metrics=run_metrics,
                registry=registry,
                failure_context=failure_context,
                workspace_dir=job_workspace_dir,
                source_profile=str(state.get("source_profile") or getattr(settings, "source_policy_mode", "open-web")),
                policy_overrides=dict(state.get("policy_overrides") or {}),
                file_inputs=file_inputs,
                mcp_config_path=getattr(settings, "mcp_config_path", None),
                mcp_servers=getattr(settings, "mcp_servers", []),
                ablation_variant=ablation_variant,
                is_follow_up=True,
            )
            units_processed += 1
            if remaining_follow_up_queries:
                remaining_follow_up_queries.pop(0)
    else:
        logger.info("🔍 Researcher 开始执行 {} 个子任务", len(tasks))
        for task in tasks:
            if max_units is not None and units_processed >= max_units:
                break
            if task.status == "completed":
                continue

            _execute_single_search(
                query=task.query,
                task=task,
                task_id=task.id,
                task_title=task.title,
                task_intent=task.intent,
                research_topic=research_topic,
                research_profile=research_profile,
                llm=llm,
                enabled_sources=settings.enabled_sources,
                max_results=settings.max_search_results,
                per_source_max_results=settings.per_source_max_results,
                per_task_selected_sources=settings.per_task_selected_sources,
                task_summaries=task_summaries,
                sources_gathered=sources_gathered,
                source_snapshots=source_snapshots,
                search_results=search_results,
                evidence_notes=evidence_notes,
                capability_plan=capability_plan,
                tool_invocations=tool_invocations,
                coverage_status=coverage_status,
                connector_health=connector_health,
                run_metrics=run_metrics,
                registry=registry,
                failure_context=failure_context,
                workspace_dir=job_workspace_dir,
                source_profile=str(state.get("source_profile") or getattr(settings, "source_policy_mode", "open-web")),
                policy_overrides=dict(state.get("policy_overrides") or {}),
                file_inputs=file_inputs,
                mcp_config_path=getattr(settings, "mcp_config_path", None),
                mcp_servers=getattr(settings, "mcp_servers", []),
                ablation_variant=ablation_variant,
                is_follow_up=False,
            )
            task.status = "completed"
            if task_summaries:
                task.summary = task_summaries[-1]
            if evidence_notes:
                latest_note = evidence_notes[-1]
                task.sources = ", ".join(f"[{item}]" for item in latest_note.source_ids)
            units_processed += 1

        remaining_follow_up_queries = []

    logger.info(
        "🔍 Researcher 执行完成: 总结数={}, 来源数={}",
        len(task_summaries),
        len(sources_gathered),
    )
    if tool_invocations:
        successful = sum(1 for invocation in tool_invocations if invocation.success)
        run_metrics.tool_use_success_rate = round(successful / len(tool_invocations), 3)

    has_pending_tasks = any(task.status != "completed" for task in tasks)
    has_more_work = bool(remaining_follow_up_queries) or has_pending_tasks

    return {
        "tasks": tasks,
        "task_summaries": task_summaries,
        "sources_gathered": sources_gathered,
        "source_snapshots": source_snapshots,
        "search_results": search_results,
        "evidence_notes": evidence_notes,
        "available_capabilities": available_capabilities,
        "capability_plan": capability_plan,
        "tool_invocations": tool_invocations,
        "coverage_status": coverage_status,
        "connector_health": {
            name: record.model_dump(mode="json") if isinstance(record, ConnectorHealthRecord) else record
            for name, record in connector_health.items()
        },
        "run_metrics": run_metrics,
        "pending_follow_up_queries": remaining_follow_up_queries,
        "status": "researched",
    }, has_more_work


def _execute_single_search(
    *,
    query: str,
    task: TaskItem | None,
    task_id: int | None,
    task_title: str,
    task_intent: str,
    research_topic: str,
    research_profile: str,
    llm,
    enabled_sources: list[str],
    max_results: int,
    per_source_max_results: int,
    per_task_selected_sources: int,
    task_summaries: list[str],
    sources_gathered: list[SourceRecord],
    source_snapshots: list[dict[str, Any]],
    search_results: list[str],
    evidence_notes: list[EvidenceNote],
    capability_plan: dict[str, list[str]],
    tool_invocations: list[ToolInvocationRecord],
    coverage_status: dict[str, bool],
    connector_health: dict[str, Any],
    run_metrics: RunMetrics,
    registry,
    failure_context: dict[str, Any],
    workspace_dir: str,
    source_profile: str,
    policy_overrides: dict[str, Any],
    file_inputs: list[str],
    mcp_config_path: str | None,
    mcp_servers: list[dict[str, Any]],
    ablation_variant: str | None,
    is_follow_up: bool,
) -> None:
    """执行单个搜索 + 总结流程。"""
    logger.info("  🔎 搜索: '{}'", query)

    active_task = task or TaskItem(
        id=task_id or 0,
        title=task_title,
        intent=task_intent,
        query=query,
        task_type=infer_task_type(query),
    )
    planned_capabilities = _filter_capabilities_for_variant(
        registry.plan_for_task(
            active_task,
            missing_aspects=list(getattr(active_task, "expected_aspects", []) or []),
            failure_context=failure_context,
        ),
        ablation_variant=ablation_variant,
    )
    capability_plan[task_title] = [capability.name for capability in planned_capabilities]
    selected_sources = _resolve_enabled_sources(planned_capabilities, enabled_sources, active_task)
    skill_capabilities = [cap for cap in planned_capabilities if cap.kind == "skill"]
    mcp_capabilities = [cap for cap in planned_capabilities if cap.kind == "mcp"]
    if skill_capabilities:
        run_metrics.skill_activation_count += 1
    if mcp_capabilities:
        run_metrics.mcp_activation_count += 1
    tool_invocations.extend(
        ToolInvocationRecord(
            capability_name=capability.name,
            kind=capability.kind,
            task_title=task_title,
            success=True,
            detail="planner-selected",
        )
        for capability in planned_capabilities
    )

    results, selected_count, rejected_count = _collect_results(
        query=query,
        task=active_task,
        task_title=task_title,
        research_profile=research_profile,
        enabled_sources=selected_sources,
        max_results=max_results,
        per_source_max_results=per_source_max_results,
        per_task_selected_sources=per_task_selected_sources,
        start_index=len(sources_gathered) + 1,
        mcp_capabilities=mcp_capabilities,
        workspace_dir=workspace_dir,
        source_profile=source_profile,
        policy_overrides=policy_overrides,
        file_inputs=file_inputs,
        source_snapshots=source_snapshots,
        connector_health=connector_health,
        mcp_config_path=mcp_config_path,
        mcp_servers=mcp_servers,
        run_metrics=run_metrics,
        is_follow_up=is_follow_up,
    )
    sources_gathered.extend(results)
    selected_results = [record for record in results if record.selected]
    run_metrics.selected_sources += selected_count
    run_metrics.rejected_sources += rejected_count
    if any(
        record.metadata.get("backend") == "duckduckgo"
        for record in results
        if record.source_type == "web"
    ):
        run_metrics.fallback_search_calls += 1

    context_records = selected_results if research_profile == "benchmark" else results
    search_context = _format_context(context_records)
    search_results.append(search_context)

    if not context_records:
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
                aspect_hits=[],
                claim_count=0,
                selected_source_ids=[],
            )
        )
        return

    if research_profile == "benchmark" and llm is None:
        summary = _build_deterministic_summary(
            task_title=task_title,
            task=active_task,
            records=context_records,
        )
    else:
        user_prompt = _build_summary_prompt(
            research_topic=research_topic,
            task_title=task_title,
            task_intent=task_intent,
            task_query=query,
            context=search_context,
            task=active_task,
            research_profile=research_profile,
            skill_capabilities=skill_capabilities,
        )
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = llm.invoke(messages)
            summary = response.content
        except Exception:
            if research_profile != "benchmark":
                raise
            logger.exception("⚠️ Benchmark profile LLM 总结失败，回退到确定性总结")
            summary = _build_deterministic_summary(
                task_title=task_title,
                task=active_task,
                records=context_records,
            )
            _append_summary(
                task_id=task_id,
                query=query,
                task_title=task_title,
                summary=summary,
                active_task=active_task,
                context_records=context_records,
                selected_results=selected_results,
                task_summaries=task_summaries,
                evidence_notes=evidence_notes,
                coverage_status=coverage_status,
            )
            logger.info("  ✅ 总结完成: '{}'", task_title)
            return

        from llm.clean import clean_llm_output

        summary = clean_llm_output(summary)
        if research_profile == "benchmark":
            summary = _repair_benchmark_summary_if_needed(
                summary=summary,
                task_title=task_title,
                task=active_task,
                records=context_records,
                selected_results=selected_results,
                run_metrics=run_metrics,
            )

    _append_summary(
        task_id=task_id,
        query=query,
        task_title=task_title,
        summary=summary,
        active_task=active_task,
        context_records=context_records,
        selected_results=selected_results,
        task_summaries=task_summaries,
        evidence_notes=evidence_notes,
        coverage_status=coverage_status,
    )
    logger.info("  ✅ 总结完成: '{}'", task_title)


def _append_summary(
    *,
    task_id: int | None,
    query: str,
    task_title: str,
    summary: str,
    active_task: TaskItem,
    context_records: list[SourceRecord],
    selected_results: list[SourceRecord],
    task_summaries: list[str],
    evidence_notes: list[EvidenceNote],
    coverage_status: dict[str, bool],
) -> None:
    aspect_hits = aspect_hits_in_text(summary, active_task.expected_aspects if active_task else [])
    for aspect in active_task.expected_aspects:
        coverage_status[aspect] = aspect in aspect_hits
    note = EvidenceNote(
        task_id=task_id,
        task_title=task_title,
        query=query,
        summary=summary,
        source_ids=[record.citation_id for record in context_records],
        aspect_hits=aspect_hits,
        claim_count=_estimate_claim_count(summary),
        selected_source_ids=[record.citation_id for record in selected_results],
    )
    existing_index = next(
        (
            index
            for index, existing_note in enumerate(evidence_notes)
            if (task_id is not None and existing_note.task_id == task_id)
            or existing_note.task_title == task_title
        ),
        None,
    )
    if existing_index is not None and existing_index < len(task_summaries):
        task_summaries[existing_index] = summary
        evidence_notes[existing_index] = note
    else:
        task_summaries.append(summary)
        evidence_notes.append(note)


def _collect_results(
    *,
    query: str,
    task: TaskItem | None,
    task_title: str,
    research_profile: str,
    enabled_sources: list[str],
    max_results: int,
    per_source_max_results: int,
    per_task_selected_sources: int,
    start_index: int,
    mcp_capabilities: list[ToolCapability],
    workspace_dir: str,
    source_profile: str,
    policy_overrides: dict[str, Any],
    file_inputs: list[str],
    source_snapshots: list[dict[str, Any]],
    connector_health: dict[str, Any],
    mcp_config_path: str | None,
    mcp_servers: list[dict[str, Any]],
    run_metrics: RunMetrics,
    is_follow_up: bool,
) -> tuple[list[SourceRecord], int, int]:
    """采集多源搜索结果。"""
    settings = get_settings()
    if not getattr(settings, "connector_substrate_enabled", True):
        return _collect_results_legacy(
            query=query,
            task=task,
            task_title=task_title,
            research_profile=research_profile,
            enabled_sources=enabled_sources,
            max_results=max_results,
            per_source_max_results=per_source_max_results,
            per_task_selected_sources=per_task_selected_sources,
            start_index=start_index,
            mcp_capabilities=mcp_capabilities,
            workspace_dir=workspace_dir,
            mcp_config_path=mcp_config_path,
            mcp_servers=mcp_servers,
            run_metrics=run_metrics,
            is_follow_up=is_follow_up,
        )
    connector_registry = _build_phase3_connector_registry(settings)
    snapshot_store = SnapshotStore(Path(workspace_dir) / getattr(settings, "snapshot_store_dirname", "snapshots"))
    policy = load_source_policy(source_profile).with_overrides(policy_overrides)

    active_task_type = task.task_type if task else infer_task_type(query)
    raw_items: list[dict[str, Any]] = []
    active_sources: list[str] = []
    case_study_task = bool(task and any(is_case_study_aspect(aspect) for aspect in task.expected_aspects))
    for source_name in enabled_sources:
        if research_profile == "benchmark" and not should_use_source(active_task_type, source_name):
            continue
        if task and task.preferred_sources and source_name not in task.preferred_sources:
            continue
        active_sources.append(source_name)

    if file_inputs and "files" not in active_sources and source_profile == "public-then-private":
        active_sources.append("files")

    for source_name in active_sources:
        limit = per_source_max_results if research_profile == "benchmark" else max_results
        connector = _resolve_connector(connector_registry, source_name)
        health = _health_record(connector_health, getattr(connector, "connector_name", str(source_name)))
        source_queries = build_source_queries(
            task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
            source_name,
        )
        if case_study_task:
            run_metrics.case_study_query_count += len(source_queries)
            if is_follow_up:
                run_metrics.case_study_rescue_calls += len(source_queries)
        if source_name == "files":
            raw_items.extend(
                _build_file_candidates(
                    file_inputs,
                    query=query,
                    task_query=task.query if task else query,
                    connector_name=getattr(connector, "connector_name", "files"),
                )
            )
            continue
        for source_query in source_queries:
            health.search_attempts += 1
            try:
                source_candidates = connector.search(source_query, max_results=limit)
            except Exception as exc:
                health.error_count += 1
                health.last_error = str(exc)
                logger.warning("connector search 失败: connector={}, error={}", source_name, exc)
                continue
            if source_candidates:
                health.search_successes += 1
            filtered = policy.filter_candidates(source_candidates)
            health.policy_blocked += len(filtered.blocked)
            for candidate in filtered.allowed:
                raw_items.append(_candidate_to_item(candidate))

    for capability in mcp_capabilities:
        try:
            source_queries = build_source_queries(
                task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
                "web",
            )
        except Exception as exc:
            logger.warning("MCP 工具调用失败: capability={}, error={}", capability.name, exc)
            continue

        for source_query in source_queries:
            try:
                mcp_items = invoke_mcp_capability(
                    capability,
                    query=source_query,
                    max_results=per_source_max_results if research_profile == "benchmark" else max_results,
                    config_path=mcp_config_path,
                    raw_servers=mcp_servers,
                    workspace_dir=workspace_dir,
                )
            except Exception as exc:
                logger.warning("MCP 工具调用失败: capability={}, error={}", capability.name, exc)
                continue

            for item in mcp_items:
                enriched = dict(item)
                enriched.setdefault("source_type", item.get("source_type", "web"))
                enriched.setdefault("query", source_query)
                enriched.setdefault("connector_name", "open_web")
                enriched.setdefault("canonical_uri", item.get("url", ""))
                enriched.setdefault("mcp_source", True)
                raw_items.append(enriched)

    selected_items: list[dict[str, Any]] = []
    rejected_count = 0
    if research_profile == "benchmark":
        selected_items, rejected_items, _ = select_sources_for_task(
            raw_items,
            task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
            per_task_limit=per_task_selected_sources,
        )
        rejected_count += len(rejected_items)
        ordered_items = list(selected_items)
    else:
        ordered_items = raw_items

    results: list[SourceRecord] = []
    citation_id = start_index
    budget_guard = BudgetGuard(
        policy.budget,
        usage=BudgetUsage(total_fetches=_total_fetch_attempts(connector_health), fetches_for_task=0),
    )
    for item in ordered_items:
        if not budget_guard.can_fetch():
            rejected_count += 1
            continue
        source_name = item.get("source_type", "web")
        connector_name = str(item.get("connector_name") or _map_source_name_to_connector(source_name))
        health = _health_record(connector_health, connector_name)
        if connector_name != "files":
            fetch_decision = policy.validate_fetch_uri(str(item.get("canonical_uri") or item.get("url") or ""))
            if not fetch_decision.allowed:
                health.policy_blocked += 1
                health.last_error = fetch_decision.reason
                rejected_count += 1
                continue
        health.fetch_attempts += 1
        try:
            fetched = _fetch_item(
                item=item,
                query=query,
                connector_registry=connector_registry,
                task_title=task_title,
            )
            snapshot = snapshot_store.persist(
                SnapshotInput(
                    connector_name=connector_name,
                    source_type=fetched.source_type,
                    canonical_uri=fetched.canonical_uri or fetched.url,
                    title=fetched.title,
                    text=fetched.text,
                    mime_type=fetched.mime_type,
                    auth_scope=fetched.auth_scope,
                    query=fetched.query,
                    metadata=fetched.freshness_metadata | fetched.metadata,
                    url=fetched.url,
                )
            )
            source_snapshots.append(snapshot.model_dump(mode="json"))
            results.append(
                SourceRecord(
                    citation_id=citation_id,
                    source_id=f"source-{citation_id}",
                    source_type=fetched.source_type,
                    query=fetched.query or query,
                    title=fetched.title,
                    canonical_uri=fetched.canonical_uri,
                    url=fetched.url or fetched.canonical_uri,
                    snippet=fetched.snippet or fetched.text[:300].replace("\n", " "),
                    task_title=task_title,
                    published_at=fetched.freshness_metadata.get("published_at"),
                    snapshot_ref=snapshot.snapshot_id,
                    fetched_at=snapshot.fetched_at,
                    mime_type=snapshot.mime_type,
                    auth_scope=snapshot.auth_scope,
                    freshness_metadata=snapshot.freshness_metadata,
                    trust_tier=_infer_trust_tier(item),
                    relevance_score=item.get("selection_score", 0.0),
                    selection_score=item.get("selection_score", 0.0),
                    selected=True,
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key not in _SOURCE_RECORD_RESERVED_KEYS
                    },
                )
            )
            budget_guard.record_fetch()
            health.fetch_successes += 1
        except Exception as exc:
            health.error_count += 1
            health.last_error = str(exc)
            rejected_count += 1
            logger.warning("connector fetch 失败: connector={}, error={}", connector_name, exc)
            continue
        citation_id += 1
    return results, len(results), rejected_count


def _collect_results_legacy(
    *,
    query: str,
    task: TaskItem | None,
    task_title: str,
    research_profile: str,
    enabled_sources: list[str],
    max_results: int,
    per_source_max_results: int,
    per_task_selected_sources: int,
    start_index: int,
    mcp_capabilities: list[ToolCapability],
    workspace_dir: str,
    mcp_config_path: str | None,
    mcp_servers: list[dict[str, Any]],
    run_metrics: RunMetrics,
    is_follow_up: bool,
) -> tuple[list[SourceRecord], int, int]:
    """phase03 关闭时保留原 collecting 语义。"""
    collectors = {
        "web": search_web,
        "github": search_github_repositories,
        "arxiv": search_arxiv_papers,
    }

    active_task_type = task.task_type if task else infer_task_type(query)
    raw_items: list[dict[str, Any]] = []
    active_sources: list[str] = []
    case_study_task = bool(task and any(is_case_study_aspect(aspect) for aspect in task.expected_aspects))
    for source_name in enabled_sources:
        if research_profile == "benchmark" and not should_use_source(active_task_type, source_name):
            continue
        if task and task.preferred_sources and source_name not in task.preferred_sources:
            continue
        active_sources.append(source_name)

    for source_name in active_sources:
        collector = collectors.get(source_name)
        if collector is None:
            continue

        limit = per_source_max_results if research_profile == "benchmark" else max_results
        source_queries = build_source_queries(
            task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
            source_name,
        )
        if case_study_task:
            run_metrics.case_study_query_count += len(source_queries)
            if is_follow_up:
                run_metrics.case_study_rescue_calls += len(source_queries)
        for source_query in source_queries:
            source_items = collector(source_query, max_results=limit)
            for item in source_items:
                enriched = dict(item)
                enriched.setdefault("source_type", source_name)
                enriched.setdefault("query", source_query)
                raw_items.append(enriched)

    for capability in mcp_capabilities:
        try:
            source_queries = build_source_queries(
                task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
                "web",
            )
        except Exception as exc:
            logger.warning("MCP 工具调用失败: capability={}, error={}", capability.name, exc)
            continue

        for source_query in source_queries:
            try:
                mcp_items = invoke_mcp_capability(
                    capability,
                    query=source_query,
                    max_results=per_source_max_results if research_profile == "benchmark" else max_results,
                    config_path=mcp_config_path,
                    raw_servers=mcp_servers,
                    workspace_dir=workspace_dir,
                )
            except Exception as exc:
                logger.warning("MCP 工具调用失败: capability={}, error={}", capability.name, exc)
                continue

            for item in mcp_items:
                enriched = dict(item)
                enriched.setdefault("source_type", item.get("source_type", "web"))
                enriched.setdefault("query", source_query)
                raw_items.append(enriched)

    selected_items: list[dict[str, Any]] = []
    if research_profile == "benchmark":
        selected_items, rejected_items, _ = select_sources_for_task(
            raw_items,
            task or TaskItem(id=0, title=task_title, intent=task_title, query=query),
            per_task_limit=per_task_selected_sources,
        )
        ordered_items = [*selected_items, *rejected_items]
    else:
        rejected_items = []
        ordered_items = raw_items

    results: list[SourceRecord] = []
    citation_id = start_index
    selected_item_ids = {id(item) for item in selected_items} if research_profile == "benchmark" else set()
    for item in ordered_items:
        source_name = item.get("source_type", "web")
        results.append(
            SourceRecord(
                citation_id=citation_id,
                source_type=item.get("source_type", source_name),
                query=item.get("query", query),
                title=item.get("title", "无标题"),
                canonical_uri=item.get("url", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                task_title=task_title,
                published_at=item.get("published_at"),
                trust_tier=_infer_trust_tier(item),
                relevance_score=item.get("selection_score", 0.0),
                selection_score=item.get("selection_score", 0.0),
                selected=id(item) in selected_item_ids if research_profile == "benchmark" else True,
                rejection_reason=item.get("rejection_reason"),
                metadata={
                    key: value
                    for key, value in item.items()
                    if key not in _SOURCE_RECORD_RESERVED_KEYS
                },
            )
        )
        citation_id += 1
    selected_count = sum(1 for record in results if record.selected)
    rejected_count = len(results) - selected_count if research_profile == "benchmark" else 0
    return results, selected_count, rejected_count


_SOURCE_RECORD_RESERVED_KEYS = {
    "index",
    "connector_name",
    "canonical_uri",
    "source_type",
    "title",
    "url",
    "snippet",
    "published_at",
    "query",
    "mcp_source",
    "selection_score",
    "rejection_reason",
}


def _map_source_name_to_connector(source_name: str) -> str:
    if source_name == "web":
        return "open_web"
    return source_name


def _resolve_connector(connector_registry, source_name: str):
    return connector_registry.get(_map_source_name_to_connector(source_name))


def _health_record(connector_health: dict[str, Any], connector_name: str) -> ConnectorHealthRecord:
    payload = connector_health.get(connector_name)
    record = (
        payload
        if isinstance(payload, ConnectorHealthRecord)
        else ConnectorHealthRecord.model_validate(payload or {"connector_name": connector_name})
    )
    connector_health[connector_name] = record
    return record


def _candidate_to_item(candidate: ConnectorCandidate) -> dict[str, Any]:
    payload = candidate.model_dump(mode="json")
    payload["url"] = candidate.canonical_uri
    payload["source_type"] = candidate.source_type
    payload["published_at"] = candidate.published_at
    payload["query"] = candidate.query
    return payload


def _build_file_candidates(
    file_inputs: list[str],
    *,
    query: str,
    task_query: str,
    connector_name: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for file_path in file_inputs:
        path = Path(file_path)
        candidates.append(
            {
                "connector_name": connector_name,
                "source_type": "files",
                "title": path.name,
                "url": path.resolve().as_uri(),
                "canonical_uri": path.resolve().as_uri(),
                "snippet": f"本地文件输入：{path.name}",
                "query": task_query or query,
                "file_path": str(path.resolve()),
                "auth_scope": "private",
            }
        )
    return candidates


def _fetch_item(*, item: dict[str, Any], query: str, connector_registry, task_title: str):
    connector_name = str(item.get("connector_name") or _map_source_name_to_connector(str(item.get("source_type") or "web")))
    if item.get("mcp_source"):
        text = str(item.get("snippet") or item.get("title") or "")
        return type(
            "McpFetchResult",
            (),
            {
                "connector_name": connector_name,
                "source_type": str(item.get("source_type") or "web"),
                "title": str(item.get("title") or "无标题"),
                "canonical_uri": str(item.get("canonical_uri") or item.get("url") or ""),
                "query": str(item.get("query") or query),
                "text": text,
                "snippet": str(item.get("snippet") or ""),
                "mime_type": "text/plain",
                "auth_scope": str(item.get("auth_scope") or "public"),
                "freshness_metadata": {
                    "published_at": item.get("published_at"),
                    "task_title": task_title,
                },
                "metadata": {
                    key: value
                    for key, value in item.items()
                    if key not in _SOURCE_RECORD_RESERVED_KEYS | {"auth_scope", "file_path"}
                },
                "url": str(item.get("url") or item.get("canonical_uri") or ""),
            },
        )()

    connector = connector_registry.get(connector_name)
    if str(item.get("source_type")) == "files":
        return connector.ingest(str(item.get("file_path")), query=str(item.get("query") or query))
    candidate = ConnectorCandidate(
        connector_name=connector_name,
        source_type=str(item.get("source_type") or "web"),
        title=str(item.get("title") or "无标题"),
        canonical_uri=str(item.get("canonical_uri") or item.get("url") or ""),
        query=str(item.get("query") or query),
        snippet=str(item.get("snippet") or ""),
        published_at=item.get("published_at"),
        auth_scope=str(item.get("auth_scope") or "public"),
        metadata={
            key: value
            for key, value in item.items()
            if key not in _SOURCE_RECORD_RESERVED_KEYS | {"auth_scope", "file_path"}
        },
    )
    return connector.fetch(candidate)


def _total_fetch_attempts(connector_health: dict[str, Any]) -> int:
    total = 0
    for payload in connector_health.values():
        record = payload if isinstance(payload, ConnectorHealthRecord) else ConnectorHealthRecord.model_validate(payload)
        total += record.fetch_attempts
    return total


def _infer_trust_tier(item: dict[str, Any]) -> int:
    override = item.get("trust_tier_override")
    if override is not None:
        return int(override)

    source_type = item.get("source_type", "web")
    url = item.get("url", "")
    if source_type == "github":
        return 5
    if source_type == "arxiv":
        return 4
    if any(
        marker in url
        for marker in (
            "github.com",
            "docs.",
            "readthedocs",
            "docs.langchain.com",
            "reference.langchain.com",
            "docs.crewai.com",
            "crewai.com",
            "microsoft.github.io",
            "openai.com",
            "anthropic.com",
            "langchain.com",
            "microsoft.com",
            "aws.amazon.com",
            "cloud.google.com",
            "salesforce.com",
            "ibm.com",
        )
    ):
        return 4
    if any(marker in url for marker in ("youtube.com", "youtu.be", "bilibili.com")):
        return 1
    if "reddit.com" in url or "facebook.com" in url or "x.com" in url:
        return 1
    return 3


def _build_summary_prompt(
    *,
    research_topic: str,
    task_title: str,
    task_intent: str,
    task_query: str,
    context: str,
    task: TaskItem | None,
    research_profile: str,
    skill_capabilities: list[ToolCapability] | None = None,
) -> str:
    prompt = SUMMARIZER_USER_PROMPT.format(
        research_topic=research_topic,
        task_title=task_title,
        task_intent=task_intent,
        task_query=task_query,
        context=context,
    )
    if research_profile != "benchmark":
        return prompt

    expected_aspects = "、".join(task.expected_aspects) if task and task.expected_aspects else "当前任务方面"
    skill_guidance = _format_skill_guidance(skill_capabilities or [])
    return (
        f"{prompt}\n\n"
        "额外约束：\n"
        f"- 必须显式回答这些方面：{expected_aspects}\n"
        "- 只允许使用提供的来源，不要引入额外事实\n"
        "- 每个核心结论后保留 [n] 形式引用\n"
        "- 若来源存在冲突，必须明确写出“存在冲突”或“证据不足”\n"
        f"{skill_guidance}"
    )


def _resolve_enabled_sources(
    planned_capabilities: list[ToolCapability],
    enabled_sources: list[str],
    task: TaskItem,
) -> list[str]:
    planned_sources = [
        capability.metadata.get("source_name")
        for capability in planned_capabilities
        if capability.kind == "builtin" and capability.metadata.get("source_name")
    ]
    if planned_sources:
        return list(dict.fromkeys(source for source in planned_sources if source in enabled_sources))
    if task.preferred_sources:
        return list(task.preferred_sources)
    return enabled_sources


def _format_skill_guidance(skill_capabilities: list[ToolCapability]) -> str:
    if not skill_capabilities:
        return ""
    descriptions = "；".join(capability.description or capability.name for capability in skill_capabilities[:2])
    return f"- 参考已激活 skill 的策略偏好：{descriptions}\n"


def _match_follow_up_task(query: str, tasks: list[TaskItem]) -> TaskItem | None:
    normalized_query = query.lower()
    generic_keywords = {
        "agent",
        "llm",
        "language",
        "model",
        "models",
        "framework",
        "frameworks",
        "use",
        "case",
        "study",
        "application",
        "applications",
        "production",
        "deployment",
        "official",
        "docs",
        "documentation",
        "overview",
        "architecture",
        "architectures",
        "最新",
        "进展",
        "案例",
        "应用",
        "架构",
    }

    best_task: TaskItem | None = None
    best_score = 0

    for task in tasks:
        score = 0
        title = task.title.lower().strip()
        if title and title in normalized_query:
            score += 80

        for aspect in task.expected_aspects:
            aspect_text = aspect.lower().strip()
            if aspect_text and aspect_text in normalized_query:
                score += 100
                continue

            keyword_hits = 0
            for keyword in extract_aspect_keywords(aspect):
                normalized_keyword = keyword.lower().strip()
                if not normalized_keyword or normalized_keyword in generic_keywords:
                    continue
                if len(normalized_keyword) <= 2 and normalized_keyword.isascii():
                    continue
                if normalized_keyword in normalized_query:
                    keyword_hits += 1
            score += keyword_hits * 10

        if task.task_type == "product" and any(
            marker in normalized_query
            for marker in ("case study", "customer story", "deployment", "production", "行业应用案例")
        ):
            score += 12

        if score > best_score:
            best_task = task
            best_score = score

    return best_task if best_score > 0 else None


def _estimate_claim_count(summary: str) -> int:
    content_lines = [
        line.strip()
        for line in summary.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not content_lines:
        return 0
    bullet_count = sum(1 for line in content_lines if line.startswith(("-", "*")) or re.match(r"^\d+\.", line))
    return bullet_count or len(content_lines)


def _build_deterministic_summary(
    *,
    task_title: str,
    task: TaskItem | None,
    records: list[SourceRecord],
) -> str:
    strong_records, weak_high_trust_records, supplementary_records = _partition_records_for_summary(records, task)
    aspect_text = "、".join(task.expected_aspects) if task and task.expected_aspects else task_title

    sections = ["### 核心结论", ""]
    if strong_records:
        sections.append(
            _append_inline_citations(
                f"本节直接覆盖方面：{aspect_text}。当前高可信来源能够直接支撑以下判断：",
                [record.citation_id for record in strong_records],
                max_count=2,
            )
        )
        for record in strong_records[:2]:
            sections.append(
                _append_inline_citations(
                    f"- {_render_record_evidence(record)}",
                    [record.citation_id],
                    max_count=1,
                )
            )
        if len(strong_records) > 2:
            sections.append(
                _append_inline_citations(
                    "其余高可信来源提供了同方向补充证据，但未在此逐条展开。",
                    [record.citation_id for record in strong_records[2:]],
                    max_count=2,
                )
            )
    elif weak_high_trust_records:
        sections.append(
            _append_inline_citations(
                f"本节覆盖方面：{aspect_text}。已检索到高可信来源，但它们主要提供背景信息而非直接证据，因此当前只能做出保守判断。",
                [record.citation_id for record in weak_high_trust_records],
                max_count=3,
            )
        )
    elif records:
        sections.append(
            _append_inline_citations(
                f"本节覆盖方面：{aspect_text}。现有高可信证据有限；基于当前公开资料，只能做出保守判断，但证据仍有限，需进一步验证：{_summarize_records(records)}。",
                [record.citation_id for record in records],
                max_count=3,
            )
        )
    else:
        sections.append(f"本节覆盖方面：{aspect_text}。当前没有可用于支撑该方面的来源。")

    sections.append("")
    sections.append("### 补充观察")
    sections.append("")
    if supplementary_records:
        sections.append(
            _append_inline_citations(
                f"中低可信补充资料还提到，{_summarize_records(supplementary_records)}。这些信息可作为背景线索，但不应单独支撑强结论。",
                [record.citation_id for record in supplementary_records],
                max_count=3,
            )
        )
    elif weak_high_trust_records:
        sections.append(
            _append_inline_citations(
                f"补充观察主要来自间接相关的高可信来源，例如：{_summarize_records(weak_high_trust_records)}。",
                [record.citation_id for record in weak_high_trust_records],
                max_count=2,
            )
        )
    else:
        citation_ids = [record.citation_id for record in strong_records or weak_high_trust_records or records]
        sections.append(
            _append_inline_citations(
                "当前未发现与核心判断明显冲突的低可信补充资料，本节以高可信来源为主。",
                citation_ids,
                max_count=2,
            )
        )

    sections.append("")
    sections.append("### 证据限制")
    sections.append("")
    if strong_records and supplementary_records:
        sections.append(
            _append_inline_citations(
                "当前核心判断主要依赖少量直接命中的高可信来源；补充资料可作为背景线索，但仍需更多独立来源或官方文档交叉验证。",
                [record.citation_id for record in [*strong_records, *supplementary_records]],
                max_count=3,
            )
        )
    elif strong_records:
        sections.append(
            _append_inline_citations(
                "当前核心判断主要依赖少量高可信来源，仍需更多独立来源或官方文档交叉验证。",
                [record.citation_id for record in strong_records],
                max_count=2,
            )
        )
    elif weak_high_trust_records:
        sections.append(
            _append_inline_citations(
                "当前虽然检索到高可信来源，但它们与本节方面的直接对应关系较弱，因此不能将这些资料视为强证据。",
                [record.citation_id for record in weak_high_trust_records],
                max_count=2,
            )
        )
    elif records:
        sections.append(
            _append_inline_citations(
                "当前仅有中低可信公开资料，结论应视为阶段性判断，仍需官方文档或论文进一步验证。",
                [record.citation_id for record in records],
                max_count=3,
            )
        )
    else:
        sections.append("当前证据不足，尚无法形成可靠判断。")

    return "\n".join(sections).strip()


def _repair_benchmark_summary_if_needed(
    *,
    summary: str,
    task_title: str,
    task: TaskItem | None,
    records: list[SourceRecord],
    selected_results: list[SourceRecord],
    run_metrics: RunMetrics,
) -> str:
    """校验 benchmark LLM 总结；若不满足最低可信度约束则回退到确定性总结。"""
    reasons = _benchmark_summary_repair_reasons(
        summary=summary,
        task=task,
        selected_results=selected_results,
    )
    if not reasons:
        return summary

    logger.warning("⚠️ benchmark 总结触发 deterministic repair: task='{}', reasons={}", task_title, reasons)
    run_metrics.summary_repair_count += 1
    if task_title not in run_metrics.summary_repair_tasks:
        run_metrics.summary_repair_tasks.append(task_title)
    return _build_deterministic_summary(task_title=task_title, task=task, records=records)


def _benchmark_summary_repair_reasons(
    *,
    summary: str,
    task: TaskItem | None,
    selected_results: list[SourceRecord],
) -> list[str]:
    """判断 benchmark LLM 总结是否需要回退为确定性版本。"""
    reasons: list[str] = []
    citation_ids = {int(match) for match in re.findall(r"\[(\d+)\]", summary)}
    if not citation_ids:
        reasons.append("missing_citations")

    expected_aspects = list(task.expected_aspects if task else [])
    if expected_aspects:
        aspect_hits = set(aspect_hits_in_text(summary, expected_aspects))
        missing_aspects = [aspect for aspect in expected_aspects if aspect not in aspect_hits]
        if missing_aspects:
            reasons.append(f"missing_aspects:{','.join(missing_aspects)}")

    high_trust_selected = [record for record in selected_results if getattr(record, "trust_tier", 3) >= 4]
    high_trust_ids = {record.citation_id for record in high_trust_selected}
    if high_trust_ids and not (citation_ids & high_trust_ids):
        reasons.append("missing_high_trust_citations")

    case_study_records = [
        record
        for record in high_trust_selected
        if str(getattr(record, "metadata", {}).get("case_study_type", "")).startswith("official_")
        or getattr(record, "metadata", {}).get("case_study_type") == "first_party_repo"
    ]
    if case_study_records:
        normalized_summary = summary.lower()
        if not any(
            marker in normalized_summary
            for marker in (
                "官方案例",
                "官方产品文档",
                "官方文档示例",
                "一手仓库",
                "customer story",
                "official",
            )
        ):
            reasons.append("missing_case_study_provenance")
    return reasons


def _summarize_records(records: list[SourceRecord], *, max_items: int = 2) -> str:
    snippets: list[str] = []
    for record in records[:max_items]:
        snippet = _clean_snippet(record.snippet)
        if snippet:
            snippets.append(f"《{record.title}》提到{snippet[:100]}")
        else:
            snippets.append(f"《{record.title}》提供了相关线索")
    return "；".join(snippets) if snippets else "当前尚无可归纳内容"


def _append_inline_citations(text: str, citation_ids: list[int], *, max_count: int) -> str:
    if not citation_ids:
        return text
    suffix = "".join(f"[{citation_id}]" for citation_id in citation_ids[:max_count])
    return f"{text} {suffix}".rstrip()


def _partition_records_for_summary(
    records: list[SourceRecord],
    task: TaskItem | None,
) -> tuple[list[SourceRecord], list[SourceRecord], list[SourceRecord]]:
    strong_records: list[SourceRecord] = []
    weak_high_trust_records: list[SourceRecord] = []
    supplementary_records: list[SourceRecord] = []
    for record in records:
        specificity = _support_specificity(record, task)
        if record.trust_tier >= 4 and specificity >= 0.5:
            strong_records.append(record)
        elif record.trust_tier >= 4 and specificity >= 0.28:
            weak_high_trust_records.append(record)
        else:
            supplementary_records.append(record)
    return strong_records, weak_high_trust_records, supplementary_records


def _support_specificity(record: SourceRecord, task: TaskItem | None) -> float:
    metadata_value = (record.metadata or {}).get("support_specificity")
    try:
        if metadata_value is not None:
            return float(metadata_value)
    except (TypeError, ValueError):
        pass
    if task is None:
        return 0.0
    normalized_text = re.sub(
        r"\s+",
        " ",
        f"{record.title} {record.snippet}".lower(),
    )
    required_terms = [term for term in task.must_include_terms if term]
    if not required_terms:
        return 0.0
    matched = 0
    for term in required_terms:
        candidate = term.lower().strip()
        if not candidate:
            continue
        if candidate in normalized_text:
            matched += 1
    return round(matched / len(required_terms), 3) if required_terms else 0.0


def _render_record_evidence(record: SourceRecord) -> str:
    snippet = _clean_snippet(record.snippet)
    if snippet:
        return f"《{record.title}》指出{snippet[:140]}"
    return f"《{record.title}》提供了与当前方面直接相关的资料"


def _clean_snippet(snippet: str) -> str:
    cleaned = re.sub(r"\s+", " ", snippet or "").strip(" 。；;:-")
    cleaned = re.sub(r"\[[^\]]+\]", "", cleaned)
    return cleaned


def _filter_capabilities_for_variant(
    capabilities: list[ToolCapability],
    *,
    ablation_variant: str | None,
) -> list[ToolCapability]:
    """按 ablation 变体裁剪可用能力。"""
    if ablation_variant in {"ours_base", "ours_verifier", "ours_gate"}:
        return [capability for capability in capabilities if capability.kind == "builtin"]
    return list(capabilities)


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
