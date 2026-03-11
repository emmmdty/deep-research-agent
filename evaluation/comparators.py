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
from workflows.states import RunMetrics, SourceRecord


COMPARATOR_ALIASES = {
    "our": "ours",
    "gpt-researcher": "gptr",
    "open_deep_research": "odr",
    "open-deep-research": "odr",
    "tongyi": "alibaba",
}


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
    metrics: dict[str, Any] = Field(default_factory=dict, description="运行与评测指标")
    error: str = Field(default="", description="错误信息")


def load_topics(
    max_topics: int = 0,
    topics_path: Path | None = None,
) -> list[BenchmarkTopic]:
    """加载标准 benchmark 主题。"""
    path = topics_path or PROJECT_ROOT / "evaluation" / "benchmarks" / "topics.json"
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    topics = [BenchmarkTopic.model_validate(item) for item in payload["topics"]]
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
    settings: Settings | None = None,
) -> ComparatorResult:
    """运行指定 comparator。"""
    settings = settings or get_settings()
    normalized = normalize_comparator_name(name)

    if normalized == "ours":
        return run_ours_comparator(topic, output_root, max_loops=max_loops)
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
) -> ComparatorResult:
    """运行当前项目自身的研究工作流。"""
    from workflows.graph import run_research

    output_dir = Path(output_root) / "ours"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{topic.id}.md"

    try:
        state = run_research(topic.topic, max_loops=max_loops)
        report = state.get("final_report") or ""
        artifact = state.get("report_artifact")
        sources = state.get("sources_gathered") or []
        run_metrics = state.get("run_metrics")
        if artifact is not None and not report:
            report = artifact.report
        if artifact is not None and not sources:
            sources = artifact.citations

        if report:
            report_path.write_text(report, encoding="utf-8")

        metrics = _runtime_metrics_dict(run_metrics)
        return ComparatorResult(
            name="ours",
            status="completed" if report else "failed",
            success=bool(report),
            report_text=report,
            report_path=str(report_path) if report else None,
            sources=_coerce_sources(sources),
            metrics=metrics,
            error="" if report else "未生成报告",
        )
    except Exception as exc:  # pragma: no cover - 通过集成测试覆盖
        logger.exception("运行 ours comparator 失败: {}", exc)
        return ComparatorResult(
            name="ours",
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


def build_report_metrics(
    *,
    report_text: str,
    topic: BenchmarkTopic,
    runtime_metrics: dict[str, Any] | None = None,
    sources: list[SourceRecord] | None = None,
) -> dict[str, Any]:
    """合并运行指标与报告质量指标。"""
    metrics = dict(runtime_metrics or {})
    metrics.update(
        evaluate_report(
            report_text,
            source_records=sources or None,
            expected_aspects=topic.expected_aspects,
        )
    )
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
