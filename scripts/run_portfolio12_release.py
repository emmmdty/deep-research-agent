"""运行 portfolio12 正式 benchmark + ablation，并打包 release 结果集。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from configs.settings import PROJECT_ROOT, SearchBackend, get_settings
from evaluation.llm_judge import LLMJudge
from scripts.run_ablation import run_ablation
from scripts.run_benchmark import (
    build_benchmark_summary,
    run_benchmark_suite,
    save_results,
    save_summary,
)
from scripts.runtime_env import load_runtime_env


def run_release(
    *,
    output_root: Path,
    env_file: str | None,
    calibration_topics: int = 2,
    max_loops: int = 2,
    topic_set: str = "portfolio12",
    release_mode: str = "hybrid",
    live_topic_ids: list[str] | None = None,
) -> dict[str, Any]:
    """运行正式 release 流程。"""
    load_runtime_env(env_file)
    output_root.mkdir(parents=True, exist_ok=True)
    live_topic_ids = live_topic_ids or (["T01", "T04", "T11"] if release_mode == "hybrid" else [])

    preflight = _run_preflight(env_file=env_file, judge_topic=f"{topic_set} judge preflight")

    live_root = output_root / "live_calibration"
    live_benchmark = _run_benchmark_release(
        output_root=live_root / "benchmark",
        env_file=env_file,
        topics_limit=calibration_topics if release_mode == "full-live" and not live_topic_ids else None,
        topic_ids=live_topic_ids if release_mode == "hybrid" else None,
        use_judge=True,
        max_loops=max_loops,
        topic_set=topic_set,
    )
    live_precomputed = _build_precomputed_results(live_benchmark["results"])
    live_ablation = _run_ablation_release(
        output_root=live_root / "ablation",
        env_file=env_file,
        use_judge=True,
        topic_ids=live_topic_ids if release_mode == "hybrid" else None,
        precomputed_results=live_precomputed,
        max_loops=max_loops,
        topic_set=topic_set,
    )
    _validate_calibration(
        benchmark_summary=live_benchmark["summary"],
        ablation_summary=live_ablation["summary"],
    )

    full_root = output_root / "full_portfolio12"
    full_benchmark = _run_benchmark_release(
        output_root=full_root / "benchmark",
        env_file=env_file,
        topics_limit=None,
        topic_ids=None,
        use_judge=release_mode == "full-live",
        max_loops=max_loops,
        topic_set=topic_set,
    )
    full_precomputed_results = _build_precomputed_results(full_benchmark["results"])
    full_ablation = _run_ablation_release(
        output_root=full_root / "ablation",
        env_file=env_file,
        use_judge=release_mode == "full-live",
        topic_ids=None,
        precomputed_results=full_precomputed_results,
        max_loops=max_loops,
        topic_set=topic_set,
    )

    manifest = _build_release_manifest(
        env_file=env_file,
        topic_set=topic_set,
        release_mode=release_mode,
        live_topic_ids=live_topic_ids,
        live_benchmark=live_benchmark,
        live_ablation=live_ablation,
        full_benchmark=full_benchmark,
        full_ablation=full_ablation,
        preflight=preflight,
        output_root=output_root,
    )
    (output_root / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_root / "RESULTS.md").write_text(
        _render_results_markdown(
            manifest=manifest,
            live_benchmark_summary=live_benchmark["summary"],
            live_ablation_summary=live_ablation["summary"],
            full_benchmark_summary=full_benchmark["summary"],
            full_ablation_summary=full_ablation["summary"],
        ),
        encoding="utf-8",
    )
    return {
        "preflight": preflight,
        "live_calibration": {
            "benchmark": live_benchmark,
            "ablation": live_ablation,
        },
        "full_portfolio12": {
            "benchmark": full_benchmark,
            "ablation": full_ablation,
        },
        "manifest": manifest,
    }


def _run_preflight(*, env_file: str | None, judge_topic: str) -> dict[str, Any]:
    """检查 judge 与主模型是否可用。"""
    load_runtime_env(env_file)
    settings = get_settings()
    llm_config = settings.get_llm_config()
    if not llm_config.get("api_key"):
        raise RuntimeError("未检测到 LLM_API_KEY，无法进行带 Judge 的正式 release 运行")

    judge = LLMJudge()
    sample_report = (
        "# 预检报告\n\n"
        "本报告用于校验 Judge 与主模型链路。系统具备概述、证据、总结和参考来源等完整结构。[1]\n\n"
        "该段落用于保证文本长度超过 Judge 的最小阈值，并模拟正式研究报告中的事实性判断与引用写法。"
        "如果 Judge 返回可解析 JSON，说明 live judge 路线可用。[2]\n\n"
        "## 参考来源\n\n"
        "[1] https://example.com/preflight/overview\n"
        "[2] https://example.com/preflight/judge\n"
    )
    scores = judge.score_report(sample_report, judge_topic)
    if not scores or not scores.get("overall"):
        raise RuntimeError(f"Judge 预检失败: {scores}")

    return {
        "judge_status": "scored",
        "judge_model": settings.judge_model or settings.llm_model_name,
        "search_backend": str(settings.search_backend.value if isinstance(settings.search_backend, SearchBackend) else settings.search_backend),
        "benchmark_health": {
            "duckduckgo_fallback": settings.search_backend == SearchBackend.DUCKDUCKGO or not bool(settings.tavily_api_key),
        },
        "judge_scores": scores,
    }


def _run_benchmark_release(
    *,
    output_root: Path,
    env_file: str | None,
    topics_limit: int | None,
    topic_ids: list[str] | None,
    use_judge: bool,
    max_loops: int,
    topic_set: str,
) -> dict[str, Any]:
    """运行正式 benchmark 并写出结果。"""
    load_runtime_env(env_file)
    from evaluation.comparators import load_topics

    topics = load_topics(topic_set=topic_set, max_topics=topics_limit or 0)
    if topic_ids:
        topic_id_set = {str(topic_id) for topic_id in topic_ids}
        topics = [topic for topic in topics if topic.id in topic_id_set]
    results = run_benchmark_suite(
        topics=topics,
        comparator_names=["ours"],
        output_root=output_root,
        use_judge=use_judge,
        max_loops=max_loops,
        research_profile="benchmark",
        env_file=env_file,
    )
    save_results(results, output_root)
    summary = build_benchmark_summary(results, comparator_name="ours")
    save_summary(summary, output_root)
    return {"results": results, "summary": summary}


def _run_ablation_release(
    *,
    output_root: Path,
    env_file: str | None,
    use_judge: bool,
    topic_ids: list[str] | None,
    precomputed_results: dict[str, dict[str, Any]],
    max_loops: int,
    topic_set: str,
) -> dict[str, Any]:
    """运行正式 ablation，并复用 benchmark 的 ours_full 结果。"""
    return run_ablation(
        output_root=output_root,
        topic_set=topic_set,
        max_topics=0,
        topic_ids=topic_ids,
        max_loops=max_loops,
        use_judge=use_judge,
        research_profile="benchmark",
        env_file=env_file,
        precomputed_results=precomputed_results,
    )


def _build_precomputed_results(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """从正式 benchmark 结果中提取 ours_full 可复用 payload。"""
    precomputed: dict[str, dict[str, Any]] = {}
    for topic_result in results:
        payload = topic_result.get("comparators", {}).get("ours")
        if payload:
            precomputed[str(topic_result["topic_id"])] = payload
    return precomputed


def _validate_calibration(*, benchmark_summary: dict[str, Any], ablation_summary: dict[str, Any]) -> None:
    """校验 2 题 calibration 是否满足进入全量运行的最低条件。"""
    if benchmark_summary.get("judge_status") != "scored":
        raise RuntimeError("calibration benchmark 未获得 judge 分数，停止正式 release")
    if ablation_summary.get("judge_status") != "scored":
        raise RuntimeError("calibration ablation 未获得 judge 分数，停止正式 release")

    deltas = ablation_summary.get("deltas_vs_base", {}).get("ours_full", {})
    if (deltas.get("judge_overall") or 0.0) <= 0:
        raise RuntimeError("calibration 未显示 ours_full 在 judge_overall 上优于 ours_base，停止正式 release")
    if (deltas.get("verification_strength_score_100") or 0.0) <= 0:
        raise RuntimeError("calibration 未显示 ours_full 在 verification_strength 上优于 ours_base，停止正式 release")


def _build_release_manifest(
    *,
    env_file: str | None,
    topic_set: str,
    release_mode: str,
    live_topic_ids: list[str],
    live_benchmark: dict[str, Any],
    live_ablation: dict[str, Any],
    full_benchmark: dict[str, Any],
    full_ablation: dict[str, Any],
    preflight: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    """生成 release manifest。"""
    settings = get_settings()
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_commit": _current_git_commit(),
        "env_file": env_file,
        "env_profile": {
            "provider": str(settings.llm_provider.value),
            "model": settings.llm_model_name,
            "judge_model": settings.judge_model or settings.llm_model_name,
            "search_backend": str(settings.search_backend.value),
        },
        "topic_set": topic_set,
        "release_mode": release_mode,
        "live_topic_ids": live_topic_ids,
        "judge_status": "hybrid" if release_mode == "hybrid" else full_benchmark["summary"].get("judge_status", "unknown"),
        "preflight": preflight,
        "live_calibration": {
            "benchmark_output_dir": str(output_root / "live_calibration" / "benchmark"),
            "ablation_output_dir": str(output_root / "live_calibration" / "ablation"),
            "judge_status": live_benchmark["summary"].get("judge_status", "unknown"),
            "benchmark_health": live_benchmark["summary"].get("benchmark_health", {}),
            "benchmark_counts": live_benchmark["summary"].get("counts", {}),
            "benchmark_scorecard": live_benchmark["summary"].get("scorecard", {}),
            "ablation_highlights": live_ablation["summary"].get("deltas_vs_base", {}),
        },
        "full_portfolio12": {
            "benchmark_output_dir": str(output_root / "full_portfolio12" / "benchmark"),
            "ablation_output_dir": str(output_root / "full_portfolio12" / "ablation"),
            "judge_status": full_benchmark["summary"].get("judge_status", "unknown"),
            "benchmark_health": full_benchmark["summary"].get("benchmark_health", {}),
            "benchmark_counts": full_benchmark["summary"].get("counts", {}),
            "benchmark_scorecard": full_benchmark["summary"].get("scorecard", {}),
            "ablation_highlights": full_ablation["summary"].get("deltas_vs_base", {}),
        },
    }


def _render_results_markdown(
    *,
    manifest: dict[str, Any],
    live_benchmark_summary: dict[str, Any],
    live_ablation_summary: dict[str, Any],
    full_benchmark_summary: dict[str, Any],
    full_ablation_summary: dict[str, Any],
) -> str:
    """生成适合简历和面试引用的 release 摘要。"""
    live_scorecard = live_benchmark_summary.get("scorecard", {})
    live_counts = live_benchmark_summary.get("counts", {})
    live_deltas = live_ablation_summary.get("deltas_vs_base", {}).get("ours_full", {})
    full_scorecard = full_benchmark_summary.get("scorecard", {})
    full_counts = full_benchmark_summary.get("counts", {})
    full_deltas = full_ablation_summary.get("deltas_vs_base", {}).get("ours_full", {})
    lines = [
        "# Portfolio12 Release Results",
        "",
        f"- Generated At: `{manifest['generated_at']}`",
        f"- Git Commit: `{manifest['git_commit']}`",
        f"- Topic Set: `{manifest['topic_set']}`",
        f"- Judge Status: `{manifest['judge_status']}`",
        f"- LLM Provider: `{manifest['env_profile']['provider']}`",
        f"- LLM Model: `{manifest['env_profile']['model']}`",
        f"- Judge Model: `{manifest['env_profile']['judge_model']}`",
        f"- Search Backend: `{manifest['env_profile']['search_backend']}`",
        f"- Release Mode: `{manifest['release_mode']}`",
        "",
        "## Live Calibration",
        "",
        f"- Topic IDs: `{', '.join(manifest.get('live_topic_ids', []))}`",
        f"- Completed: `{live_counts.get('completed', 0)}` / `{live_counts.get('completed', 0) + live_counts.get('failed', 0)}`",
        f"- Quality Gate Passed: `{live_counts.get('quality_gate_passed', 0)}`",
        f"- Research Reliability Avg: `{_fmt(live_scorecard.get('research_reliability_score_100', {}).get('avg'))}`",
        f"- System Controllability Avg: `{_fmt(live_scorecard.get('system_controllability_score_100', {}).get('avg'))}`",
        f"- Report Quality Avg: `{_fmt(live_scorecard.get('report_quality_score_100', {}).get('avg'))}`",
        f"- Evaluation Reproducibility Avg: `{_fmt(live_scorecard.get('evaluation_reproducibility_score_100', {}).get('avg'))}`",
        "",
        "## Live Ablation Highlights",
        "",
        f"- Delta vs Base (Judge Overall): `{_fmt(live_deltas.get('judge_overall'))}`",
        f"- Delta vs Base (Quality Gate Pass Rate): `{_fmt(live_deltas.get('quality_gate_pass_rate'))}`",
        f"- Delta vs Base (Verification Strength): `{_fmt(live_deltas.get('verification_strength_score_100'))}`",
        "",
        "## Full Portfolio12 Benchmark",
        "",
        f"- Completed: `{full_counts.get('completed', 0)}` / `{full_counts.get('completed', 0) + full_counts.get('failed', 0)}`",
        f"- Quality Gate Passed: `{full_counts.get('quality_gate_passed', 0)}`",
        f"- Research Reliability Avg: `{_fmt(full_scorecard.get('research_reliability_score_100', {}).get('avg'))}`",
        f"- System Controllability Avg: `{_fmt(full_scorecard.get('system_controllability_score_100', {}).get('avg'))}`",
        f"- Report Quality Avg: `{_fmt(full_scorecard.get('report_quality_score_100', {}).get('avg'))}`",
        f"- Evaluation Reproducibility Avg: `{_fmt(full_scorecard.get('evaluation_reproducibility_score_100', {}).get('avg'))}`",
        "",
        "## Full Ablation Highlights",
        "",
        f"- Delta vs Base (Judge Overall): `{_fmt(full_deltas.get('judge_overall'))}`",
        f"- Delta vs Base (Quality Gate Pass Rate): `{_fmt(full_deltas.get('quality_gate_pass_rate'))}`",
        f"- Delta vs Base (Verification Strength): `{_fmt(full_deltas.get('verification_strength_score_100'))}`",
        "",
        "## Resume-Ready Findings",
        "",
        f"- 在 live calibration 主题 `{', '.join(manifest.get('live_topic_ids', []))}` 上保留 judge 评分链路，并完成 `{live_counts.get('completed', 0)}` 个主题。",
        f"- 在全量 `{manifest['topic_set']}` benchmark 中完成 `{full_counts.get('completed', 0)}` 个主题，`research_reliability_score_100` 平均达到 `{_fmt(full_scorecard.get('research_reliability_score_100', {}).get('avg'))}`。",
        f"- 相比 `ours_base`，`ours_full` 在 live calibration 的 `judge_overall` 上提升 `{_fmt(live_deltas.get('judge_overall'))}`，在 `verification_strength_score_100` 上提升 `{_fmt(live_deltas.get('verification_strength_score_100'))}`。",
        "",
        "## Known Limits",
        "",
        "- 若 GitHub/Tavily 发生限流或回退，相关信号会记录在 `benchmark_health`，不会被静默吞掉。",
        "- LLM-as-Judge 结果受当前 judge 模型版本影响，复现时应保留同一 env profile。",
    ]
    return "\n".join(lines)


def _current_git_commit() -> str:
    """读取当前工作树对应 commit。"""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except Exception as exc:  # pragma: no cover - 系统环境差异
        logger.warning("读取 git commit 失败: {}", exc)
        return "unknown"


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 portfolio12 正式 benchmark + ablation release")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--env-file", type=str, required=True, help="显式指定运行时 env 文件")
    parser.add_argument("--topic-set", type=str, default="portfolio12", help="正式主题集")
    parser.add_argument("--calibration-topics", type=int, default=2, help="正式运行前的校准题数")
    parser.add_argument("--release-mode", type=str, default="hybrid", choices=["hybrid", "full-live"], help="发布模式：代表题 live + 全量可复现，或全量 live")
    parser.add_argument("--live-topic-ids", type=str, default="T01,T04,T11", help="hybrid 模式下 live judge 主题 ID")
    parser.add_argument("--max-loops", type=int, default=2, help="最大研究循环次数")
    args = parser.parse_args()

    run_id = time.strftime("%Y%m%d-%H%M%S")
    output_root = (
        Path(args.output_dir)
        if args.output_dir
        else PROJECT_ROOT / "workspace" / "releases" / f"{args.topic_set}-{run_id}"
    )
    outcome = run_release(
        output_root=output_root,
        env_file=args.env_file,
        calibration_topics=args.calibration_topics,
        max_loops=args.max_loops,
        topic_set=args.topic_set,
        release_mode=args.release_mode,
        live_topic_ids=[item.strip() for item in args.live_topic_ids.split(",") if item.strip()],
    )
    logger.info(
        "portfolio12 release 完成: full_completed={}, judge_status={}, output={}",
        outcome["full_portfolio12"]["benchmark"]["summary"].get("counts", {}).get("completed"),
        outcome["manifest"].get("judge_status"),
        output_root,
    )


if __name__ == "__main__":
    main()
