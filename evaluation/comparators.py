"""统一 comparator registry 与竞品运行适配。"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from pydantic import BaseModel, Field

from configs.settings import PROJECT_ROOT, Settings, get_settings
from evaluation.metrics import evaluate_report
from workflows.states import MemoryStats, ReportArtifact, RunMetrics, SourceRecord, TopicSpec


COMPARATOR_ALIASES = {
    "our": "ours",
    "gpt-researcher": "gptr",
    "open_deep_research": "odr",
    "open-deep-research": "odr",
    "tongyi": "alibaba",
}

INTERNAL_ABLATION_VARIANTS = {"ours_base", "ours_verifier", "ours_gate", "ours_full"}


class BenchmarkTopic(BaseModel):
    """单个 benchmark 主题。"""

    id: str = Field(description="主题 ID")
    topic: str = Field(description="研究主题")
    difficulty: str = Field(default="medium", description="难度等级")
    expected_aspects: list[str] = Field(default_factory=list, description="预期覆盖方面")
    min_sources: int = Field(default=0, description="最少来源数量")
    min_words: int = Field(default=0, description="最少字数")


class ComparatorResult(BaseModel):
    """统一 comparator 输出。"""

    name: str = Field(description="comparator 名称")
    status: str = Field(default="completed", description="completed/failed/skipped")
    success: bool = Field(default=False, description="是否运行成功")
    report_text: str = Field(default="", description="最终报告文本")
    report_path: Optional[str] = Field(default=None, description="报告文件路径")
    sources: list[SourceRecord] = Field(default_factory=list, description="结构化来源")
    report_artifact: Optional[ReportArtifact] = Field(default=None, description="结构化报告产物")
    metrics: dict[str, Any] = Field(default_factory=dict, description="运行与评测指标")
    error: str = Field(default="", description="错误信息")


def load_topics(
    max_topics: int = 0,
    topics_path: Path | None = None,
    topic_set: str = "default",
) -> list[BenchmarkTopic]:
    """加载标准 benchmark 主题。"""
    path = topics_path or PROJECT_ROOT / "evaluation" / "benchmarks" / "topics.json"
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    topics = [BenchmarkTopic.model_validate(item) for item in payload["topics"]]
    if topic_set == "local3":
        indexed = {topic.id: topic for topic in topics}
        topics = [
            indexed["T01"],
            indexed["T02"],
            BenchmarkTopic(
                id="T06C",
                topic="openclaw安装教程",
                difficulty="easy",
                expected_aspects=[
                    "安装前置条件 / 依赖",
                    "下载或获取源码",
                    "编译或安装步骤",
                    "常见错误与排查",
                    "运行验证",
                ],
                min_sources=4,
                min_words=2000,
            ),
        ]
    elif topic_set == "portfolio12":
        base_topics = [
            topic
            for topic in topics
            if topic.id != "T06"
        ]
        topics = [
            *base_topics[:5],
            BenchmarkTopic(
                id="T06C",
                topic="openclaw安装教程",
                difficulty="easy",
                expected_aspects=[
                    "安装前置条件 / 依赖",
                    "下载或获取源码",
                    "编译或安装步骤",
                    "常见错误与排查",
                    "运行验证",
                ],
                min_sources=4,
                min_words=2000,
            ),
            *(topic for topic in base_topics[5:] if topic.id in {"T07", "T08"}),
            *_portfolio_topics(),
        ]
    return topics[:max_topics] if max_topics > 0 else topics


def resolve_comparators(
    settings: Settings,
    requested: list[str] | None = None,
    include_optional: list[str] | None = None,
) -> list[str]:
    """解析最终要执行的 comparator 名单。"""
    names = requested or list(settings.enabled_comparators)
    resolved: list[str] = []
    for raw_name in [*names, *(include_optional or [])]:
        normalized = normalize_comparator_name(raw_name)
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def normalize_comparator_name(name: str) -> str:
    """规范化 comparator 名称。"""
    lowered = name.strip().lower()
    return COMPARATOR_ALIASES.get(lowered, lowered)


def run_comparator(
    name: str,
    topic: BenchmarkTopic,
    output_root: Path,
    *,
    max_loops: int = 2,
    research_profile: str = "default",
    settings: Settings | None = None,
    ablation_variant: str | None = None,
) -> ComparatorResult:
    """运行指定 comparator。"""
    settings = settings or get_settings()
    normalized = normalize_comparator_name(name)

    if normalized == "ours":
        return run_ours_comparator(
            topic,
            output_root,
            max_loops=max_loops,
            research_profile=research_profile,
            comparator_name="ours",
            ablation_variant=ablation_variant,
        )
    if normalized in INTERNAL_ABLATION_VARIANTS:
        resolved_variant = normalized if ablation_variant is None else ablation_variant
        return run_ours_comparator(
            topic,
            output_root,
            max_loops=max_loops,
            research_profile=research_profile,
            comparator_name=normalized,
            ablation_variant=resolved_variant,
        )
    if normalized == "gptr":
        return run_gptr_comparator(topic, output_root, settings=settings)
    if normalized == "odr":
        return run_configured_comparator(
            name="odr",
            topic=topic,
            output_root=output_root,
            command_template=settings.open_deep_research_command,
            report_dir=settings.open_deep_research_report_dir,
        )
    if normalized == "alibaba":
        use_import = settings.alibaba_runner_mode.strip().lower() == "import"
        if use_import:
            return run_import_report_comparator(
                name="alibaba",
                topic=topic,
                report_dir=settings.alibaba_report_dir,
            )
        return run_configured_comparator(
            name="alibaba",
            topic=topic,
            output_root=output_root,
            command_template=settings.alibaba_command,
            report_dir=settings.alibaba_report_dir,
        )
    if normalized == "gemini":
        if not settings.gemini_enabled:
            return ComparatorResult(
                name="gemini",
                status="skipped",
                success=False,
                error="gemini comparator disabled",
            )
        return run_configured_comparator(
            name="gemini",
            topic=topic,
            output_root=output_root,
            command_template=settings.gemini_command,
            report_dir=settings.gemini_report_dir,
            allow_missing=bool(settings.gemini_allowlist_required),
        )

    raise ValueError(f"不支持的 comparator: {name}")


def run_ours_comparator(
    topic: BenchmarkTopic,
    output_root: Path,
    *,
    max_loops: int = 2,
    research_profile: str = "default",
    comparator_name: str = "ours",
    ablation_variant: str | None = None,
) -> ComparatorResult:
    """运行当前项目自身的研究工作流。"""
    from workflows.graph import run_research

    output_dir = Path(output_root) / comparator_name
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{topic.id}.md"

    try:
        state = run_research(
            topic.topic,
            max_loops=max_loops,
            topic_spec=TopicSpec.model_validate(topic.model_dump()),
            research_profile=research_profile,
            ablation_variant=ablation_variant,
        )
        report = state.get("final_report") or ""
        artifact = state.get("report_artifact")
        sources = state.get("sources_gathered") or []
        run_metrics = state.get("run_metrics")
        memory_stats = None
        if artifact is not None and not report:
            report = artifact.report
        if artifact is not None and not sources:
            sources = artifact.citations
        if artifact is not None:
            memory_stats = artifact.memory_stats

        if report:
            report_path.write_text(report, encoding="utf-8")

        metrics = _runtime_metrics_dict(run_metrics)
        if memory_stats is not None:
            metrics.update(memory_stats.model_dump())
        if sources:
            metrics.update(
                evaluate_report(
                    report,
                    source_records=_coerce_sources(sources),
                    expected_aspects=topic.expected_aspects,
                    quality_gate_status=metrics.get("quality_gate_status"),
                    report_artifact=artifact if isinstance(artifact, ReportArtifact) else None,
                    memory_stats=memory_stats,
                    runtime_metrics=run_metrics,
                )
            )
            metrics.update(_build_scorecard_metrics(metrics))
        raw_status = str(state.get("status", "completed" if report else "failed"))
        status = "failed" if raw_status == "failed_quality_gate" else raw_status
        if not report and status not in {"failed", "skipped"}:
            status = "failed"
        error = str(state.get("error") or "").strip()
        return ComparatorResult(
            name=comparator_name,
            status=status,
            success=bool(report),
            report_text=report,
            report_path=str(report_path) if report else None,
            sources=_coerce_sources(sources),
            report_artifact=artifact if isinstance(artifact, ReportArtifact) else None,
            metrics=metrics,
            error="" if report else (error or "未生成报告"),
        )
    except Exception as exc:  # pragma: no cover - 通过集成测试覆盖
        logger.exception("运行 ours comparator 失败: {}", exc)
        return ComparatorResult(
            name=comparator_name,
            status="failed",
            success=False,
            error=str(exc),
        )


def run_gptr_comparator(
    topic: BenchmarkTopic,
    output_root: Path,
    *,
    settings: Settings,
    timeout_seconds: int = 900,
) -> ComparatorResult:
    """运行 GPT Researcher comparator。"""
    from scripts.run_gptr_isolated import build_runner_environment

    candidate = settings.gpt_researcher_python
    if not candidate:
        fallback = PROJECT_ROOT / "venv_gptr" / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        candidate = str(fallback)

    python_path = Path(candidate)
    if not python_path.exists():
        return ComparatorResult(
            name="gptr",
            status="skipped",
            success=False,
            error=f"GPT Researcher Python 不存在: {python_path}",
        )

    output_dir = Path(output_root) / "gptr"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{topic.id}.md"
    meta_path = output_dir / f"{topic.id}_meta.json"
    command = [
        str(python_path),
        str(PROJECT_ROOT / "scripts" / "run_gptr_isolated.py"),
        "--topic",
        topic.topic,
        "--output",
        str(report_path),
        "--meta",
        str(meta_path),
    ]
    return _run_subprocess_comparator(
        name="gptr",
        command=command,
        report_path=report_path,
        meta_path=meta_path,
        timeout_seconds=timeout_seconds,
        env=build_runner_environment(),
    )


def run_configured_comparator(
    *,
    name: str,
    topic: BenchmarkTopic,
    output_root: Path,
    command_template: str | None,
    report_dir: str | None,
    allow_missing: bool = False,
    timeout_seconds: int = 900,
) -> ComparatorResult:
    """按命令模板或报告导入目录运行外部 comparator。"""
    if command_template:
        output_dir = Path(output_root) / name
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"{topic.id}.md"
        meta_path = output_dir / f"{topic.id}_meta.json"
        formatted = command_template.format(
            topic=topic.topic,
            topic_id=topic.id,
            report_path=report_path,
            meta_path=meta_path,
            output_dir=output_dir,
            project_root=PROJECT_ROOT,
        )
        return _run_subprocess_comparator(
            name=name,
            command=shlex.split(formatted),
            report_path=report_path,
            meta_path=meta_path,
            timeout_seconds=timeout_seconds,
            env=os.environ.copy(),
        )

    if report_dir:
        return run_import_report_comparator(name=name, topic=topic, report_dir=report_dir)

    status = "skipped" if allow_missing else "failed"
    return ComparatorResult(
        name=name,
        status=status,
        success=False,
        error=f"{name} comparator 未配置 command 或 report_dir",
    )


def run_import_report_comparator(
    *,
    name: str,
    topic: BenchmarkTopic,
    report_dir: str | Path | None,
) -> ComparatorResult:
    """从已有报告目录导入 comparator 结果。"""
    if not report_dir:
        return ComparatorResult(
            name=name,
            status="skipped",
            success=False,
            error=f"{name} comparator 未配置报告目录",
        )

    base_dir = Path(report_dir)
    report_path = base_dir / f"{topic.id}.md"
    if not report_path.exists():
        candidates = sorted(base_dir.glob(f"{topic.id}*.md"))
        report_path = candidates[0] if candidates else report_path

    if not report_path.exists():
        return ComparatorResult(
            name=name,
            status="skipped",
            success=False,
            error=f"{name} comparator 报告不存在: {report_path}",
        )

    meta_path = base_dir / f"{topic.id}_meta.json"
    meta = _read_json(meta_path) if meta_path.exists() else {}

    return ComparatorResult(
        name=name,
        status=str(meta.get("status", "completed")),
        success=bool(meta.get("success", True)),
        report_text=report_path.read_text(encoding="utf-8"),
        report_path=str(report_path),
        metrics={
            "time_seconds": meta.get("time_seconds", 0.0),
            "llm_calls": meta.get("llm_calls", 0),
            "search_calls": meta.get("search_calls", 0),
            "total_tokens": meta.get("total_tokens", 0),
        },
        error=str(meta.get("error", "")),
    )


def _portfolio_topics() -> list[BenchmarkTopic]:
    """返回用于作品集展示的 12 题扩展 benchmark。"""
    return [
        BenchmarkTopic(
            id="T09",
            topic="LangGraph、CrewAI、AutoGen 在多智能体编排上的差异",
            difficulty="medium",
            expected_aspects=["核心抽象", "状态管理", "工具调用", "适用场景", "工程权衡"],
            min_sources=5,
            min_words=2500,
        ),
        BenchmarkTopic(
            id="T10",
            topic="企业级 AI Agent 系统如何设计记忆与上下文管理",
            difficulty="medium",
            expected_aspects=["短期记忆", "长期记忆", "检索策略", "上下文压缩", "可靠性风险"],
            min_sources=5,
            min_words=2500,
        ),
        BenchmarkTopic(
            id="T11",
            topic="使用 MCP 为研究型 Agent 接入外部工具的最佳实践",
            difficulty="medium",
            expected_aspects=["MCP 基本概念", "工具发现", "权限与安全", "错误恢复", "实际接入模式"],
            min_sources=4,
            min_words=2200,
        ),
        BenchmarkTopic(
            id="T12",
            topic="AI Agent 研究报告的评测方法与可靠性指标设计",
            difficulty="medium",
            expected_aspects=["评测目标", "引用与证据", "自动化 Judge", "可复现性", "局限与风险"],
            min_sources=5,
            min_words=2500,
        ),
    ]


def build_report_metrics(
    *,
    report_text: str,
    topic: BenchmarkTopic,
    runtime_metrics: dict[str, Any] | None = None,
    sources: list[SourceRecord] | None = None,
    memory_stats: MemoryStats | None = None,
    report_artifact: ReportArtifact | None = None,
) -> dict[str, Any]:
    """合并运行指标与报告质量指标。"""
    if memory_stats is None and report_artifact is not None:
        memory_stats = report_artifact.memory_stats

    metrics = dict(runtime_metrics or {})
    metrics.update(
        evaluate_report(
            report_text,
            source_records=sources or None,
            expected_aspects=topic.expected_aspects,
            quality_gate_status=metrics.get("quality_gate_status"),
            report_artifact=report_artifact,
            memory_stats=memory_stats,
            runtime_metrics=runtime_metrics,
        )
    )
    if "quality_gate_status" in metrics and "quality_gate_passed" not in metrics:
        metrics["quality_gate_passed"] = metrics["quality_gate_status"] == "passed"
    if memory_stats is not None:
        metrics.update(memory_stats.model_dump())
    metrics.update(_build_scorecard_metrics(metrics))
    metrics["meets_min_words"] = metrics.get("word_count", 0) >= topic.min_words
    metrics["meets_min_sources"] = metrics.get("source_coverage", 0) >= topic.min_sources
    return metrics


def _run_subprocess_comparator(
    *,
    name: str,
    command: list[str],
    report_path: Path,
    meta_path: Path,
    timeout_seconds: int,
    env: dict[str, str],
) -> ComparatorResult:
    """统一处理 subprocess comparator。"""
    start = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ComparatorResult(
            name=name,
            status="failed",
            success=False,
            error=f"执行超时（{timeout_seconds}s）",
        )
    except Exception as exc:  # pragma: no cover - 防御分支
        return ComparatorResult(
            name=name,
            status="failed",
            success=False,
            error=str(exc),
        )

    meta = _read_json(meta_path) if meta_path.exists() else {}
    elapsed = round(time.time() - start, 2)
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    success = bool(meta.get("success", completed.returncode == 0 and bool(report_text)))
    status = str(meta.get("status", "completed" if success else "failed"))
    error = str(meta.get("error", "")).strip()
    if completed.returncode != 0 and not error:
        error = (completed.stderr or completed.stdout or f"{name} comparator 执行失败").strip()

    metrics = {
        "time_seconds": meta.get("time_seconds", elapsed),
        "llm_calls": meta.get("llm_calls", 0),
        "search_calls": meta.get("search_calls", 0),
        "total_tokens": meta.get("total_tokens", 0),
    }
    return ComparatorResult(
        name=name,
        status=status,
        success=success,
        report_text=report_text,
        report_path=str(report_path) if report_path.exists() else None,
        metrics=metrics,
        error=error,
    )


def _runtime_metrics_dict(metrics: RunMetrics | dict[str, Any] | None) -> dict[str, Any]:
    """把运行指标标准化为字典。"""
    if metrics is None:
        return {}
    if isinstance(metrics, RunMetrics):
        payload = metrics.model_dump()
        payload["total_tokens"] = metrics.total_tokens
        return payload
    payload = dict(metrics)
    if "total_tokens" not in payload:
        payload["total_tokens"] = int(payload.get("total_input_tokens", 0)) + int(
            payload.get("total_output_tokens", 0)
        )
    return payload


def _build_scorecard_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """把细粒度评测信号聚合成更适合展示的分数卡。"""

    total_evidence_units = float(metrics.get("total_evidence_units", 0) or 0)
    quality_gate_status = str(metrics.get("quality_gate_status") or "unchecked")
    missing_verification_penalty = 25.0 if total_evidence_units <= 0 else 45.0
    missing_entity_penalty = 35.0 if total_evidence_units <= 0 else 55.0
    verification_component = metrics.get("verification_strength_score_100")
    if verification_component is None:
        verification_component = missing_verification_penalty
    entity_component = metrics.get("entity_resolution_score_100")
    if entity_component is None:
        entity_component = missing_entity_penalty
    if quality_gate_status in {"skipped", "unchecked"}:
        verification_component = min(float(verification_component), 40.0)
        entity_component = min(float(entity_component), 50.0)

    reliability_components = [
        metrics.get("high_trust_aspect_score_100"),
        metrics.get("cross_source_corroboration_score_100"),
        verification_component,
        entity_component,
        metrics.get("citation_alignment_score_100"),
        metrics.get("conflict_disclosure_score_100"),
        metrics.get("evidence_novelty_score_100"),
        metrics.get("support_specificity_score_100"),
        metrics.get("case_study_strength_score_100"),
    ]
    research_reliability = _mean_score(reliability_components)

    aspect_score = float(metrics.get("aspect_coverage", 0.0) or 0.0) * 100
    report_quality = _mean_score(
        [
            aspect_score,
            metrics.get("coverage_balance_score_100"),
            metrics.get("structure_completeness_score_100"),
        ]
    )

    quality_gate_margin = _mean_score(
        [
            metrics.get("high_trust_aspect_score_100"),
            verification_component,
            entity_component,
        ]
    )

    selected_sources = float(metrics.get("selected_sources", 0) or 0)
    rejected_sources = float(metrics.get("rejected_sources", 0) or 0)
    selection_precision = (
        selected_sources / (selected_sources + rejected_sources)
        if (selected_sources + rejected_sources) > 0
        else 0.5
    )
    search_calls = float(metrics.get("search_calls", 0) or 0)
    fallback_search_calls = float(metrics.get("fallback_search_calls", 0) or 0)
    fallback_resilience = 1.0 - min(fallback_search_calls / search_calls, 1.0) if search_calls > 0 else 1.0
    tool_use_success = float(metrics.get("tool_use_success_rate", 0.0) or 0.0)
    system_controllability = round(
        100
        * (
            0.35 * tool_use_success
            + 0.15 * fallback_resilience
            + 0.15 * selection_precision
            + 0.15 * ((quality_gate_margin or 0.0) / 100)
            + 0.20 * ((metrics.get("recovery_resilience_score_100", 0.0) or 0.0) / 100)
        ),
        3,
    )

    return {
        "quality_gate_margin_100": quality_gate_margin,
        "research_reliability_score_100": research_reliability,
        "system_controllability_score_100": system_controllability,
        "report_quality_score_100": report_quality,
    }


def _mean_score(values: list[Any]) -> float:
    valid = [float(value) for value in values if value is not None]
    if not valid:
        return 0.0
    return round(sum(valid) / len(valid), 3)


def _coerce_sources(raw_sources: list[Any]) -> list[SourceRecord]:
    """把来源列表规范化为 SourceRecord。"""
    sources: list[SourceRecord] = []
    for item in raw_sources:
        if isinstance(item, SourceRecord):
            sources.append(item)
        elif isinstance(item, dict):
            sources.append(SourceRecord.model_validate(item))
    return sources


def _read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))
