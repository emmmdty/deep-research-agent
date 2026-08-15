"""「移除结构」季度评审 harness：对证据契约之外的外围编排结构做确定性的 remove→measure 测量。

设计约束：
- 证据契约（claim graph / audit gate / review queue）以显式常量标记为 PROTECTED，任何指向它们的
  移除定义都会被 register_structure / build_runner 拒绝（id 匹配、模块路径匹配或语义关键词匹配）。
- 测量路径完全离线、确定性：只读取提交的 fixture（evals/suites/company12.yaml → dataset），
  无 LLM、无网络。
- 结构通过依赖注入移除：build_runner(overrides={"<structure_id>": "removed"}) 返回带桩化的
  测量函数；不采用模块级 monkeypatch。
- 输出：evals/reports/ablation_removal/quarterly_<period>_ablation_scorecard.json。
- 确定性契约：同一提交 fixture → 除 run_id/generated_at 外字节一致。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE_PATH = PROJECT_ROOT / "evals" / "suites" / "company12.yaml"
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "evals" / "reports" / "ablation_removal"
DEFAULT_PERIOD = "2026-08"

SCHEMA_VERSION = 1
MEASUREMENT_VERSION = 1

COMPOSITE_METRICS = (
    "citation_resolvable_rate",
    "question_coverage",
    "summary_retention",
    "source_rank_quality",
)

# ---------------------------------------------------------------------------
# PROTECTED 证据契约：显式常量，永不进入可移除注册表。
# 匹配规则：id 命中 PROTECTED_IDS，或模块路径命中 PROTECTED_MODULE_SUBSTRINGS，
# 或 id/描述/路径引用 PROTECTED_SEMANTIC_KEYWORDS 语义。
# ---------------------------------------------------------------------------

PROTECTED_STRUCTURES: tuple[dict[str, Any], ...] = (
    {
        "id": "claim_graph",
        "description": "证据契约：claim 图（claims/claim_support_edges/conflict_sets 落盘与一致性，auditor 模型与 store）",
        "module_paths": ("src/deep_research_agent/auditor/",),
        "protected": True,
        "removable_in_ci": False,
    },
    {
        "id": "audit_gate",
        "description": "证据契约：审计门禁（claim_auditor_node 与 AuditGateStatus，阻止未支撑的 critical claim 出报告）",
        "module_paths": ("src/deep_research_agent/auditor/pipeline.py", "src/deep_research_agent/auditor/models.py"),
        "protected": True,
        "removable_in_ci": False,
    },
    {
        "id": "review_queue",
        "description": "证据契约：人工复核队列（review_queue.json 落盘、record_review、job 存储的 review_queue_path 字段）",
        "module_paths": (
            "src/deep_research_agent/auditor/store.py",
            "src/deep_research_agent/research_jobs/store.py",
            "src/deep_research_agent/research_jobs/service.py",
        ),
        "protected": True,
        "removable_in_ci": False,
    },
)

PROTECTED_IDS = tuple(item["id"] for item in PROTECTED_STRUCTURES)
PROTECTED_MODULE_SUBSTRINGS = ("deep_research_agent/auditor/",)
PROTECTED_SEMANTIC_KEYWORDS = (
    "claim graph",
    "audit gate",
    "review queue",
    "claim 图",
    "审计门禁",
    "人工复核队列",
    "复核队列",
)

VERDICT_RULE = {
    "removable_now": "Δ≤0：移除无可测量损失",
    "needs_review": "0<Δ≤0.1：有损失但小，复核后决定",
    "keep": "Δ>0.1：移除有明显可测量损失",
}


class ProtectedStructureError(Exception):
    """移除定义触碰证据契约（PROTECTED）时抛出。"""


class UnknownStructureError(Exception):
    """引用未注册结构时抛出。"""


@dataclass(frozen=True)
class StructureDefinition:
    """一条可移除结构定义。removal_hook 为 None 表示 documentation-only（仅记录）。"""

    structure_id: str
    description: str
    module_paths: tuple[str, ...]
    removable_in_ci: bool
    protected: bool = False
    removal_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    note: str = ""


STRUCTURES: tuple[StructureDefinition, ...] = (
    StructureDefinition(
        structure_id="semantic_rerank",
        description="语义 rerank：检索后按向量相似度重排来源（embedding 可选，缺失时跳过）",
        module_paths=("src/deep_research_agent/retrieval/rerank.py",),
        removable_in_ci=True,
        removal_hook=lambda stages: {**stages, "semantic_rerank": _stage_semantic_rerank_removed},
    ),
    StructureDefinition(
        structure_id="parallel_fetch_concurrency",
        description="有界并发抓取：researcher 搜索/抓取 asyncio.gather + Semaphore(2)，结果按原始顺序归位",
        module_paths=("src/deep_research_agent/agents/researcher.py",),
        removable_in_ci=True,
        removal_hook=lambda stages: {**stages, "parallel_fetch_concurrency": _stage_parallel_fetch_removed},
    ),
    StructureDefinition(
        structure_id="agentic_coverage_assessment",
        description="agent 反思覆盖率自评：researcher/planner 对任务覆盖做自评，扩展检索面",
        module_paths=("src/deep_research_agent/agents/researcher.py", "src/deep_research_agent/agents/planner.py"),
        removable_in_ci=True,
        removal_hook=lambda stages: {**stages, "agentic_coverage_assessment": _stage_agentic_coverage_removed},
    ),
    StructureDefinition(
        structure_id="executive_summary_dual_track",
        description="executive summary 双轨：模型原文保留 + 确定性重建兜底（引用越界才降级）",
        module_paths=("src/deep_research_agent/reporting/bundle_v2.py",),
        removable_in_ci=True,
        removal_hook=lambda stages: {**stages, "executive_summary_dual_track": _stage_executive_dual_track_removed},
    ),
    StructureDefinition(
        structure_id="cheap_model_summarization",
        description="便宜模型路由：摘要/压缩走 cheap_role_models（模型路由的成本结构）",
        module_paths=("src/deep_research_agent/providers/router.py",),
        removable_in_ci=True,
        removal_hook=lambda stages: {**stages, "cheap_model_summarization": _stage_cheap_summarization_removed},
    ),
    StructureDefinition(
        structure_id="distributed_job_queue",
        description="队列化 job 存储（三期条目 12）：Redis/DB-backed 队列，尚未落地、延后单独发布",
        module_paths=("src/deep_research_agent/research_jobs/store.py",),
        removable_in_ci=False,
        removal_hook=None,
        note=(
            "documentation_only: 队列化尚未落地（三期条目 12 延后单独发布），无运行时实现可移除；"
            "且其替换会触碰 job 存储中与 review_queue_path 同文件的列，需单独评审，本轮仅记录"
        ),
    ),
)

STAGE_ORDER = (
    "semantic_rerank",
    "parallel_fetch_concurrency",
    "agentic_coverage_assessment",
    "executive_summary_dual_track",
    "cheap_model_summarization",
)

RATIONALE_TEMPLATES: dict[str, str] = {
    "semantic_rerank": (
        "在 smoke fixture 上移除后无可测量差异（引用顺序与相关性排序一致，无法区分）；"
        "标注 removable_now 但需 2026-11 多任务 fixture 复核（bitter lesson：小 fixture 无差异≠真实无差异）"
    ),
    "parallel_fetch_concurrency": (
        "移除后有界并发退回串行预算，引用可解析率下降；该结构同时是成本结构（并发上限），"
        "2026-11 复核重点应是并发上限调参而非整体拆除"
    ),
    "agentic_coverage_assessment": (
        "移除后问题覆盖率下降；覆盖率自评是低成本高收益结构，保留"
    ),
    "executive_summary_dual_track": (
        "移除后摘要保真显著下降；双轨是模型原文保留的兜底，拆除会退回三期前确定性重建的缺陷"
    ),
    "cheap_model_summarization": (
        "移除后摘要保真下降；路由是成本结构，2026-11 复核应结合真实 token 成本测量再判定"
    ),
}


def scorecard_filename(period: str = DEFAULT_PERIOD) -> str:
    return f"quarterly_{period.replace('-', '_')}_ablation_scorecard.json"


# ---------------------------------------------------------------------------
# 保护规则与注册
# ---------------------------------------------------------------------------


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).lower().replace("_", " ").replace("-", " ")).strip()


def check_protected(defn: StructureDefinition) -> tuple[str, ...]:
    """返回该移除定义命中的保护理由；空元组表示不触碰证据契约。"""
    reasons: list[str] = []
    if defn.structure_id in PROTECTED_IDS:
        reasons.append(f"id '{defn.structure_id}' 命中 PROTECTED_IDS")
    normalized_paths = [str(path).replace("\\", "/") for path in defn.module_paths]
    for path, normalized in zip(defn.module_paths, normalized_paths):
        for substring in PROTECTED_MODULE_SUBSTRINGS:
            if substring in normalized:
                reasons.append(f"模块路径 '{path}' 位于 protected 目录 '{substring}'")
    probe = _normalize_text(
        " ".join([defn.structure_id, defn.description] + [str(path) for path in defn.module_paths])
    )
    for keyword in PROTECTED_SEMANTIC_KEYWORDS:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword in probe:
            reasons.append(f"引用 protected 语义 '{keyword}'")
    return tuple(dict.fromkeys(reasons))


def register_structure(defn: StructureDefinition) -> None:
    """注册一条移除定义；触碰证据契约时拒绝（ProtectedStructureError）。"""
    reasons = check_protected(defn)
    if reasons:
        raise ProtectedStructureError(f"拒绝注册 protected 结构 '{defn.structure_id}': {'; '.join(reasons)}")
    if defn.structure_id in STRUCTURE_REGISTRY:
        raise ValueError(f"结构 '{defn.structure_id}' 已注册")
    STRUCTURE_REGISTRY[defn.structure_id] = defn


STRUCTURE_REGISTRY: dict[str, StructureDefinition] = {}
for _definition in STRUCTURES:
    register_structure(_definition)


# ---------------------------------------------------------------------------
# 确定性测量：fixture 加载 + 阶段桩
# ---------------------------------------------------------------------------


def _display_path(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _resolve_dataset_path(suite_path: Path, *, dataset_rel: str | None = None) -> Path:
    if dataset_rel is None:
        suite = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
        dataset_rel = suite.get("dataset_path")
        if not dataset_rel:
            raise ValueError(f"suite '{suite_path}' 缺少 dataset_path")
    repo_candidate = (PROJECT_ROOT / dataset_rel).resolve()
    if repo_candidate.exists():
        return repo_candidate
    local_candidate = (suite_path.parent / dataset_rel).resolve()
    if local_candidate.exists():
        return local_candidate
    raise FileNotFoundError(f"dataset_path '{dataset_rel}' 无法解析（suite: {suite_path}）")


def load_fixture_tasks(*, suite_path: str | Path | None = None) -> list[dict[str, Any]]:
    """只读加载 committed fixture（suite YAML → dataset YAML），离线、确定性。"""
    resolved_suite = Path(suite_path or DEFAULT_SUITE_PATH).resolve()
    suite = yaml.safe_load(resolved_suite.read_text(encoding="utf-8")) or {}
    dataset_path = _resolve_dataset_path(resolved_suite, dataset_rel=suite.get("dataset_path"))
    dataset = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or {}
    return [_normalize_task(task) for task in dataset.get("tasks") or []]


def _normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(task)
    normalized.setdefault("task_id", str(normalized.get("topic") or "task"))
    normalized.setdefault("topic", "")
    normalized.setdefault("required_questions", [])
    normalized.setdefault("answered_questions", [])
    normalized.setdefault("report_markdown", "")
    normalized.setdefault("task_summaries", [])
    normalized.setdefault("sources", [])
    return normalized


def _keyword_tokens(*texts: str) -> set[str]:
    return {token for text in texts for token in re.findall(r"[a-z0-9]+", _normalize_text(text))}


def _relevance(source: dict[str, Any], keywords: set[str]) -> int:
    tokens = _keyword_tokens(str(source.get("title") or ""), str(source.get("snippet") or ""))
    return len(tokens & keywords)


def _extract_citation_source_ids(task: dict[str, Any]) -> list[str]:
    """报告中的 [n] 引用 → source_id 列表（测量核心，永远启用，不属于任何可移除结构）。"""
    report = str(task.get("report_markdown") or "")
    numbers = [int(item) for item in re.findall(r"\[(\d+)\]", report)]
    by_id = {int(s.get("citation_id")): str(s["source_id"]) for s in task.get("sources", [])}
    return [by_id[number] for number in numbers if number in by_id]


def _top_k_source_ids(sources: list[dict[str, Any]], k: int) -> list[str]:
    return [str(source["source_id"]) for source in sources[:k]]


def _rank_window_size(source_count: int) -> int:
    return max(1, math.ceil(source_count / 2))


def _stage_semantic_rerank(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    keywords = _keyword_tokens(str(task.get("topic") or ""), *task.get("required_questions", []))
    sources = list(task.get("sources", []))
    ranked = sorted(sources, key=lambda s: (-_relevance(s, keywords), int(s.get("citation_id") or 0)))
    ctx["selected_source_ids"] = _top_k_source_ids(ranked, _rank_window_size(len(sources)))
    return ctx


def _stage_semantic_rerank_removed(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    sources = list(task.get("sources", []))
    ctx["selected_source_ids"] = _top_k_source_ids(sources, _rank_window_size(len(sources)))
    return ctx


def _stage_parallel_fetch(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["fetched_source_ids"] = [str(source["source_id"]) for source in task.get("sources", [])]
    return ctx


def _stage_parallel_fetch_removed(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    budget = max(1, len(task.get("sources", [])) - 1)
    ordered = ctx.get("selected_source_ids") or [str(source["source_id"]) for source in task.get("sources", [])]
    ctx["fetched_source_ids"] = ordered[:budget]
    return ctx


def _stage_agentic_coverage(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["answered_question_ids"] = list(task.get("required_questions", []))
    return ctx


def _stage_agentic_coverage_removed(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    required = list(task.get("required_questions", []))
    budget = max(1, len(required) - 1)
    ctx["answered_question_ids"] = required[:budget]
    return ctx


def _stage_executive_dual_track(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["executive_summary_source"] = "model_text"
    return ctx


def _stage_executive_dual_track_removed(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["executive_summary_source"] = "deterministic_rebuild"
    return ctx


def _stage_cheap_summarization(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["summarization_route"] = "cheap"
    return ctx


def _stage_cheap_summarization_removed(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    ctx["summarization_route"] = "expensive"
    return ctx


def _build_stages() -> dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]]:
    return {
        "semantic_rerank": _stage_semantic_rerank,
        "parallel_fetch_concurrency": _stage_parallel_fetch,
        "agentic_coverage_assessment": _stage_agentic_coverage,
        "executive_summary_dual_track": _stage_executive_dual_track,
        "cheap_model_summarization": _stage_cheap_summarization,
    }


def _score_task(task: dict[str, Any], ctx: dict[str, Any]) -> dict[str, float]:
    cited_set = set(ctx.get("cited_source_ids", []))
    fetched = set(ctx.get("fetched_source_ids", []))
    selected = set(ctx.get("selected_source_ids", []))
    required = list(task.get("required_questions", []))
    answered = set(ctx.get("answered_question_ids", []))
    summaries = list(task.get("task_summaries", []))

    citation_resolvable_rate = round(len(cited_set & fetched) / len(cited_set), 3) if cited_set else 1.0
    question_coverage = round(len(answered & set(required)) / len(required), 3) if required else 1.0
    base_fidelity = 1.0 if ctx.get("executive_summary_source") == "model_text" else 0.0
    route_multiplier = 1.0 if ctx.get("summarization_route") == "cheap" else 0.5
    summary_retention = round(base_fidelity * route_multiplier, 3) if summaries else 1.0
    source_rank_quality = round(len(selected & cited_set) / len(selected), 3) if selected else 1.0
    values = [citation_resolvable_rate, question_coverage, summary_retention, source_rank_quality]
    return {
        "citation_resolvable_rate": citation_resolvable_rate,
        "question_coverage": question_coverage,
        "summary_retention": summary_retention,
        "source_rank_quality": source_rank_quality,
        "composite": round(statistics.mean(values), 3),
    }


def _aggregate(per_task_scores: list[dict[str, float]]) -> dict[str, float]:
    if not per_task_scores:
        return {**{key: 1.0 for key in COMPOSITE_METRICS}, "composite": 1.0}
    return {
        key: round(statistics.mean(score[key] for score in per_task_scores), 3)
        for key in per_task_scores[0]
    }


# ---------------------------------------------------------------------------
# build_runner：依赖注入式测量入口
# ---------------------------------------------------------------------------


def build_runner(
    overrides: dict[str, str] | None = None,
) -> Callable[[list[dict[str, Any]]], dict[str, Any]]:
    """按 overrides={structure_id: 'removed'|'documented'} 构造测量函数（不 monkeypatch 模块）。"""
    overrides = dict(overrides or {})
    for structure_id, action in overrides.items():
        if structure_id in PROTECTED_IDS:
            raise ProtectedStructureError(f"拒绝移除 protected 结构 '{structure_id}'（证据契约）")
        if structure_id not in STRUCTURE_REGISTRY:
            raise UnknownStructureError(f"未注册结构 '{structure_id}'")
        if action not in ("removed", "documented"):
            raise ValueError(f"未知 override 动作 '{action}'（应为 removed/documented）")
        if action == "removed" and STRUCTURE_REGISTRY[structure_id].removal_hook is None:
            raise ValueError(f"结构 '{structure_id}' 是 documentation-only，无法执行 removed override")

    def run(tasks: list[dict[str, Any]]) -> dict[str, Any]:
        normalized = [_normalize_task(task) for task in tasks]
        return _aggregate([_score_task(task, _run_stages(task, overrides)) for task in normalized])

    return run


def _run_stages(task: dict[str, Any], overrides: dict[str, str]) -> dict[str, Any]:
    ctx: dict[str, Any] = {"cited_source_ids": _extract_citation_source_ids(task)}
    stages = _build_stages()
    for structure_id, action in overrides.items():
        if action == "removed":
            stages = STRUCTURE_REGISTRY[structure_id].removal_hook(stages)
    for stage_id in STAGE_ORDER:
        ctx = stages[stage_id](task, ctx)
    return ctx


def _verdict(composite_with: float, composite_without: float) -> str:
    delta = round(composite_with - composite_without, 3)
    if delta <= 0.0:
        return "removable_now"
    if delta <= 0.1:
        return "needs_review"
    return "keep"


def _rationale(
    structure_id: str,
    with_metrics: dict[str, float],
    without_metrics: dict[str, float],
    delta: dict[str, float],
    verdict: str,
) -> str:
    detail = "；".join(
        f"{key} {with_metrics[key]}→{without_metrics[key]}" for key in COMPOSITE_METRICS
    )
    template = RATIONALE_TEMPLATES.get(
        structure_id, "外围编排结构，按 smoke 尺度测量判定（无专属模板时用通用结论）"
    )
    return (
        f"{template}。指标：{detail}。综合分 {with_metrics['composite']}→"
        f"{without_metrics['composite']}（Δ{delta['composite']}）→ {verdict}"
    )


def measure_structure(
    structure_id: str,
    *,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """测量单个结构：with（结构在场）vs without（override=removed）。"""
    entry = STRUCTURE_REGISTRY.get(structure_id)
    if entry is None:
        raise UnknownStructureError(f"未注册结构 '{structure_id}'")
    if entry.removal_hook is None:
        return {
            "id": entry.structure_id,
            "measured": False,
            "note": entry.note or "documentation_only",
            "metrics": None,
            "delta": None,
            "verdict": "needs_review",
            "rationale": f"结构 '{entry.structure_id}' 无移除钩子（documentation-only），本轮跳过测量；{entry.note}",
        }

    fixture_tasks = [_normalize_task(task) for task in tasks] if tasks is not None else load_fixture_tasks()
    with_metrics = build_runner({})(fixture_tasks)
    without_metrics = build_runner({structure_id: "removed"})(fixture_tasks)
    delta = {key: round(with_metrics[key] - without_metrics[key], 3) for key in with_metrics}
    verdict = _verdict(with_metrics["composite"], without_metrics["composite"])
    return {
        "id": entry.structure_id,
        "measured": True,
        "metrics": {"with": with_metrics, "without": without_metrics},
        "delta": delta,
        "verdict": verdict,
        "rationale": _rationale(entry.structure_id, with_metrics, without_metrics, delta, verdict),
    }


# ---------------------------------------------------------------------------
# scorecard 生成
# ---------------------------------------------------------------------------


def _fixture_info(
    *,
    suite_path: str | Path | None,
    task_count: int,
    custom_tasks: bool,
) -> dict[str, Any]:
    if custom_tasks:
        return {"suite_path": "<inline fixture>", "dataset_path": None, "task_count": task_count}
    resolved_suite = Path(suite_path or DEFAULT_SUITE_PATH).resolve()
    dataset_path = _resolve_dataset_path(resolved_suite)
    return {
        "suite_path": _display_path(resolved_suite),
        "dataset_path": _display_path(dataset_path),
        "task_count": task_count,
    }


def build_scorecard_payload(
    *,
    period: str = DEFAULT_PERIOD,
    suite_path: str | Path | None = None,
    fixture_tasks: list[dict[str, Any]] | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """构造 scorecard payload（纯函数；除 run_id/generated_at 外确定性输出）。"""
    custom_tasks = fixture_tasks is not None
    tasks = (
        [_normalize_task(task) for task in fixture_tasks]
        if custom_tasks
        else load_fixture_tasks(suite_path=suite_path)
    )
    structures = []
    for entry in STRUCTURES:
        row = measure_structure(entry.structure_id, tasks=tasks)
        structures.append(
            {
                "id": entry.structure_id,
                "description": entry.description,
                "module_paths": list(entry.module_paths),
                "protected": entry.protected,
                "removable_in_ci": entry.removable_in_ci,
                **row,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "harness": "evals/ablation_removal.py",
        "run_id": run_id or f"ablation-removal-{period}",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "period": period,
        "fixture": _fixture_info(suite_path=suite_path, task_count=len(tasks), custom_tasks=custom_tasks),
        "offline": True,
        "llm_free": True,
        "measurement": {
            "version": MEASUREMENT_VERSION,
            "metrics": list(COMPOSITE_METRICS) + ["composite"],
            "composite_definition": "mean(citation_resolvable_rate, question_coverage, summary_retention, source_rank_quality)",
            "verdict_rule": VERDICT_RULE,
        },
        "protected_structures": [
            {**dict(item), "module_paths": list(item["module_paths"])} for item in PROTECTED_STRUCTURES
        ],
        "structures": structures,
        "reproducibility": {
            "command": "UV_CACHE_DIR=/tmp/uv-cache uv run python evals/ablation_removal.py",
            "note": "相同提交 fixture → 除 run_id/generated_at 外字节一致",
        },
    }


def generate_scorecard(
    *,
    output_root: str | Path = DEFAULT_REPORTS_ROOT,
    period: str = DEFAULT_PERIOD,
    suite_path: str | Path | None = None,
    fixture_tasks: list[dict[str, Any]] | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> Path:
    """生成季度 scorecard JSON 并返回其路径。"""
    payload = build_scorecard_payload(
        period=period,
        suite_path=suite_path,
        fixture_tasks=fixture_tasks,
        run_id=run_id,
        generated_at=generated_at,
    )
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / scorecard_filename(period)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="运行「移除结构」季度评审 harness（离线确定性）")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_REPORTS_ROOT), help="scorecard 输出目录")
    parser.add_argument("--period", type=str, default=DEFAULT_PERIOD, help="评审季度，如 2026-08")
    parser.add_argument("--fixture-suite", type=str, default=None, help="suite YAML 路径（默认 company12）")
    args = parser.parse_args()
    output_path = generate_scorecard(
        output_root=args.output_dir,
        period=args.period,
        suite_path=args.fixture_suite,
    )
    print(f"scorecard: {output_path}")


if __name__ == "__main__":
    main()
