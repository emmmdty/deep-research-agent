"""Normalized head-to-head A/B harness between two pipelines or two models.

遵循 run_benchmark(*, request, descriptor) 模式，注册名为 ``head_to_head``
（registry 自动暴露 `benchmark run --benchmark head_to_head`）。

设计：
- runner 可注入（测试注入确定性 fake）；未注入时从配置 `runner_a` / `runner_b`
  解析（模块路径，模块须暴露 ``run_pipeline(task) -> str``）。
- 生产环境默认 runner：`v1_orchestrator_runner`（legacy orchestrator-v1，
  离线确定性、无需凭据）与 `scheduler_v2_runner`（scheduler-v2 真实管线，
  离线时产出 honest empty bundle）。
- 任务集从配置 `task_spec_path`（JSON：{"tasks": [...]}）读取，与其余
  benchmark 的 dataset manifest 形态一致；评分复用 DRB 的
  binary/recall/f1/difference 模式（离线确定性，无 judge LLM、无网络）。
"""

from __future__ import annotations

import importlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from deep_research_agent.evals.external.benchmarks.drb import _default_mode, _score_for_mode
from deep_research_agent.evals.external.contracts import (
    BenchmarkIntegrityReport,
    BenchmarkRunManifest,
    BenchmarkRunRequest,
    BenchmarkTaskResult,
    BenchmarkTaskSpec,
    HeadToHeadScorecard,
    HeadToHeadTaskRow,
)
from deep_research_agent.evals.external.manifests import write_benchmark_artifacts

PROJECT_ROOT = Path(__file__).resolve().parents[5]

Runner = Callable[[BenchmarkTaskSpec], str]


def run_benchmark(
    *,
    request: BenchmarkRunRequest,
    descriptor,
    baseline_runner: Runner | None = None,
    alternative_runner: Runner | None = None,
) -> dict[str, Any]:
    """Run a normalized A/B comparison and persist its canonical artifacts."""

    config = _load_config(request.config_path)
    task_specs = _load_task_specs(config)
    if task_specs is None:
        return _blocked_result(
            request,
            descriptor,
            "head_to_head requires task_spec_path in config (runner config example in evals/README.md)",
        )
    runner_a = baseline_runner or _resolve_runner(config, "runner_a")
    runner_b = alternative_runner or _resolve_runner(config, "runner_b")
    if runner_a is None or runner_b is None:
        return _blocked_result(
            request,
            descriptor,
            "head_to_head requires baseline/alternative runners (injectable or "
            "config runner_a/runner_b; no credentials, offline deterministic scoring)",
        )

    started_at = _utc_now()
    rows, task_results = _run_head_to_head(task_specs, runner_a, runner_b)
    aggregate = _aggregate(rows)

    runner_a_name = _runner_name(runner_a, config.get("runner_a"), "a")
    runner_b_name = _runner_name(runner_b, config.get("runner_b"), "b")
    scorecard = HeadToHeadScorecard(
        benchmark="head_to_head",
        status="completed",
        runner_a=runner_a_name,
        runner_b=runner_b_name,
        metric="task_score",
        task_count=len(rows),
        per_task=rows,
        aggregate=aggregate,
        notes=["Offline deterministic scoring against task expected_answer; runner errors score as 0."],
    )

    official_scores = {
        "benchmark": "head_to_head",
        "status": "completed",
        "metric": scorecard.metric,
        "runner_a": runner_a_name,
        "runner_b": runner_b_name,
        "score_a_mean": aggregate["score_a_mean"],
        "score_b_mean": aggregate["score_b_mean"],
        "delta_mean": aggregate["delta_mean"],
        "winner_by_metric": aggregate["winner_by_metric"],
    }
    internal_diagnostics = {
        "benchmark": "head_to_head",
        "task_count": len(task_specs),
        "completed_count": len(task_specs),
        "config_path": request.config_path,
        "task_spec_path": config.get("task_spec_path"),
        "adapter_mode": descriptor.adapter_mode,
        "role": descriptor.role,
        "runner_a": runner_a_name,
        "runner_b": runner_b_name,
        "wins": aggregate["wins"],
        "offline": True,
    }
    manifest = BenchmarkRunManifest(
        benchmark="head_to_head",
        title=config.get("title", descriptor.title),
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="completed",
        subset=request.subset or config.get("subset"),
        started_at=started_at,
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path,
        task_count=len(task_specs),
        completed_count=len(task_specs),
        official_metrics=official_scores,
        internal_metrics=internal_diagnostics,
        notes=list(config.get("notes") or [])
        + ["Scored deterministically offline; no judge LLM and no network access."],
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "offline_deterministic_scoring", "scoring": "drb_score_modes"},
    )
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores=official_scores,
        internal_diagnostics=internal_diagnostics,
        task_results=task_results,
        integrity_report=BenchmarkIntegrityReport(
            benchmark="head_to_head",
            status="passed",
            guards=list(descriptor.integrity_guards),
            summary="Head-to-head ran with injectable runners; scoring is deterministic and offline.",
        ),
    )
    scorecard_path = Path(request.output_root) / "head_to_head_scorecard.json"
    scorecard_path.write_text(
        json.dumps(scorecard.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "benchmark": "head_to_head",
        "status": "completed",
        "output_root": str(Path(request.output_root).resolve()),
        "artifacts": artifacts,
        "scorecard_path": str(scorecard_path),
        "official_metrics": manifest.official_metrics,
        "internal_metrics": manifest.internal_metrics,
    }


def v1_orchestrator_runner(task: BenchmarkTaskSpec) -> str:
    """真实 orchestrator-v1 管线：离线确定性报告，无需凭据。"""

    from legacy.workflows.graph import run_research

    result = run_research(task.prompt, max_loops=1)
    return str(result.get("final_report", ""))


def scheduler_v2_runner(task: BenchmarkTaskSpec) -> str:
    """真实 scheduler-v2 管线：离线时产出 honest empty bundle 报告文本。"""

    from configs.settings import get_settings

    from deep_research_agent.gateway.cli import _build_job_service, _submit_cli_v2

    settings = get_settings()
    service = _build_job_service()
    job = _submit_cli_v2(
        service,
        topic=task.prompt,
        max_loops=1,
        source_profile="company_broad",
        allow_domains=[],
        deny_domains=[],
        connector_budget=None,
        start_worker=True,
        settings=settings,
    )
    while job.status not in {"completed", "failed", "cancelled"}:
        time.sleep(0.5)
        job = service.get(job.job_id)
    report = "（scheduler-v2 未产出报告）"
    try:
        payload = json.loads(Path(job.report_bundle_path).read_text(encoding="utf-8"))
        report = payload.get("report_markdown") or payload.get("report_text") or report
    except (OSError, ValueError):
        pass
    return report


def _run_head_to_head(
    task_specs: list[BenchmarkTaskSpec],
    runner_a: Runner,
    runner_b: Runner,
) -> tuple[list[HeadToHeadTaskRow], list[BenchmarkTaskResult]]:
    rows: list[HeadToHeadTaskRow] = []
    task_results: list[BenchmarkTaskResult] = []
    for task in task_specs:
        prediction_a = _safe_predict(runner_a, task)
        prediction_b = _safe_predict(runner_b, task)
        task_type = str(task.metadata.get("task_type") or "binary")
        mode = str(task.metadata.get("score_mode") or _default_mode(task_type))
        score_a = _score_for_mode(mode, task.expected_answer or "", prediction_a)
        score_b = _score_for_mode(mode, task.expected_answer or "", prediction_b)
        rows.append(
            HeadToHeadTaskRow(
                task_id=task.task_id,
                prompt=task.prompt,
                expected_answer=task.expected_answer,
                prediction_a=prediction_a,
                prediction_b=prediction_b,
                score_a=score_a,
                score_b=score_b,
                delta=round(score_a - score_b, 6),
            )
        )
        for side, score, prediction in (
            ("a", score_a, prediction_a),
            ("b", score_b, prediction_b),
        ):
            task_results.append(
                BenchmarkTaskResult(
                    benchmark="head_to_head",
                    task_id=task.task_id,
                    status="completed",
                    prompt=task.prompt,
                    prediction=prediction,
                    expected_answer=task.expected_answer,
                    official_metrics={"runner": side, "score_mode": mode, "task_score": score},
                    internal_metrics={"side": side},
                    notes=["Deterministic offline scoring against task expected_answer."],
                    metadata=task.metadata,
                )
            )
    return rows, task_results


def _safe_predict(runner: Runner, task: BenchmarkTaskSpec) -> str:
    try:
        prediction = runner(task)
    except Exception:
        return "__runner_error__"
    return str(prediction)


def _aggregate(rows: list[HeadToHeadTaskRow]) -> dict[str, object]:
    if not rows:
        return {
            "score_a_mean": 0.0,
            "score_b_mean": 0.0,
            "delta_mean": 0.0,
            "wins": {"a": 0, "b": 0, "tie": 0},
            "winner_by_metric": {"task_score": "tie"},
        }
    scores_a = [row.score_a or 0.0 for row in rows]
    scores_b = [row.score_b or 0.0 for row in rows]
    mean_a = round(sum(scores_a) / len(scores_a), 6)
    mean_b = round(sum(scores_b) / len(scores_b), 6)
    wins = {"a": 0, "b": 0, "tie": 0}
    for row in rows:
        if row.score_a > row.score_b:
            wins["a"] += 1
        elif row.score_b > row.score_a:
            wins["b"] += 1
        else:
            wins["tie"] += 1
    winner = "a" if mean_a > mean_b else "b" if mean_b > mean_a else "tie"
    return {
        "score_a_mean": mean_a,
        "score_b_mean": mean_b,
        "delta_mean": round(mean_a - mean_b, 6),
        "wins": wins,
        "winner_by_metric": {"task_score": winner},
    }


def _load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}
    resolved = (PROJECT_ROOT / config_path).resolve()
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"head_to_head config must be a YAML mapping: {resolved}")
    return payload


def _load_task_specs(config: dict[str, Any]) -> list[BenchmarkTaskSpec] | None:
    task_spec_path = config.get("task_spec_path")
    if not isinstance(task_spec_path, str) or not task_spec_path:
        return None
    path = (PROJECT_ROOT / task_spec_path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not tasks:
        raise ValueError(f"task_spec 缺少 tasks: {path}")
    return [BenchmarkTaskSpec.model_validate(task) for task in tasks]


def _resolve_runner(config: dict[str, Any], key: str) -> Runner | None:
    reference = config.get(key)
    if not isinstance(reference, str) or not reference:
        return None
    module_path, _, attribute = reference.partition(":")
    module = importlib.import_module(module_path)
    runner = getattr(module, attribute or "run_pipeline", None)
    if not callable(runner):
        raise ValueError(f"runner {reference!r} 不可调用")
    return runner


def _runner_name(runner: Runner, reference: Any, fallback: str) -> str:
    if isinstance(reference, str) and reference:
        return reference
    return getattr(runner, "__name__", fallback)


def _blocked_result(request: BenchmarkRunRequest, descriptor, reason: str) -> dict[str, Any]:
    manifest = BenchmarkRunManifest(
        benchmark="head_to_head",
        title=descriptor.title,
        adapter_mode=descriptor.adapter_mode,
        role=descriptor.role,
        status="blocked",
        started_at=_utc_now(),
        completed_at=_utc_now(),
        output_root=str(Path(request.output_root).resolve()),
        config_path=request.config_path,
        task_count=0,
        completed_count=0,
        notes=[reason],
        integrity_guards=list(descriptor.integrity_guards),
        environment={"runner": "offline_deterministic_scoring"},
    )
    artifacts = write_benchmark_artifacts(
        output_root=Path(request.output_root),
        manifest=manifest,
        official_scores={"status": "blocked", "reason": reason},
        internal_diagnostics={"status": "blocked", "reason": reason},
        task_results=[],
        integrity_report=BenchmarkIntegrityReport(
            benchmark="head_to_head",
            status="blocked",
            guards=list(descriptor.integrity_guards),
            summary=reason,
        ),
    )
    return {
        "benchmark": "head_to_head",
        "status": "blocked",
        "output_root": str(Path(request.output_root).resolve()),
        "artifacts": artifacts,
        "notes": [reason],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
