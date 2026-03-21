"""local3 benchmark 自动优化编排脚本。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from configs.settings import PROJECT_ROOT, get_settings
from evaluation.comparators import load_topics
from scripts.run_benchmark import (
    build_benchmark_summary,
    run_benchmark_suite,
    save_results,
    save_summary,
)

load_dotenv(PROJECT_ROOT / ".env")


DEFAULT_THRESHOLDS = {
    "completed": 3,
    "aspect_coverage_avg": 0.85,
    "quality_gate_passed": 3,
}


def _normalize_summary_payload(summary: dict[str, Any]) -> dict[str, Any]:
    """为测试桩或外部 summary 补齐缺省字段。"""
    return {
        "generated_at": summary.get("generated_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
        "comparator": summary.get("comparator", "ours"),
        "results": summary.get("results", []),
        "counts": summary.get("counts", {}),
        "aggregates": summary.get("aggregates", {}),
        "rankings": summary.get("rankings", {}),
    }


def summary_meets_thresholds(summary: dict[str, Any], thresholds: dict[str, Any] | None = None) -> bool:
    """判断当前 benchmark summary 是否达标。"""
    thresholds = thresholds or DEFAULT_THRESHOLDS
    completed = summary.get("counts", {}).get("completed", 0)
    quality_gate_passed = summary.get("counts", {}).get("quality_gate_passed", 0)
    aspect_avg = summary.get("aggregates", {}).get("aspect_coverage", {}).get("avg") or 0.0
    return (
        completed >= thresholds["completed"]
        and quality_gate_passed >= thresholds["quality_gate_passed"]
        and aspect_avg >= thresholds["aspect_coverage_avg"]
    )


def build_failure_analysis(
    *,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    """根据结果生成失败分析。"""
    failing_topics: list[dict[str, Any]] = []
    for topic_result in results:
        payload = topic_result.get("comparators", {}).get("ours", {})
        metrics = payload.get("metrics", {})
        status = payload.get("status", "failed")
        quality_gate_passed = bool(metrics.get("quality_gate_passed", False))
        aspect_coverage = metrics.get("aspect_coverage", 0.0) or 0.0
        if status == "completed" and quality_gate_passed and aspect_coverage >= DEFAULT_THRESHOLDS["aspect_coverage_avg"]:
            continue

        failing_topics.append(
            {
                "topic_id": topic_result.get("topic_id"),
                "topic": topic_result.get("topic"),
                "status": status,
                "aspect_coverage": aspect_coverage,
                "quality_gate_passed": quality_gate_passed,
                "quality_gate_fail_reason": metrics.get("quality_gate_status", status),
                "high_trust_source_ratio": metrics.get("high_trust_source_ratio", 0.0),
                "entity_consistency_score": metrics.get("entity_consistency_score", 1.0),
                "off_topic_reject_count": metrics.get("off_topic_reject_count", 0),
                "selected_source_coverage": metrics.get("selected_source_coverage", 0),
                "missing_aspects": metrics.get("missing_aspects", []),
                "selected_sources_by_aspect": metrics.get("selected_sources_by_aspect", {}),
                "capability_plan": metrics.get("capability_plan", {}),
            }
        )

    analysis = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "counts": summary.get("counts", {}),
        "aggregates": summary.get("aggregates", {}),
        "failing_topics": failing_topics,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "failure_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return analysis


def build_strategy_patch_plan(
    *,
    summary: dict[str, Any],
    failure_analysis: dict[str, Any],
    output_root: Path,
    round_index: int,
) -> dict[str, Any]:
    """基于当前 round 结果生成策略补丁建议。"""
    actions: list[dict[str, str]] = []
    aspect_avg = summary.get("aggregates", {}).get("aspect_coverage", {}).get("avg") or 0.0
    if aspect_avg < DEFAULT_THRESHOLDS["aspect_coverage_avg"]:
        actions.append(
            {
                "action": "tighten_queries",
                "reason": "方面覆盖不足，增加 official-first 与 aspect-specific 查询词。",
            }
        )

    if summary.get("counts", {}).get("quality_gate_passed", 0) < DEFAULT_THRESHOLDS["quality_gate_passed"]:
        actions.append(
            {
                "action": "increase_high_trust_mix",
                "reason": "质量门控未通过，提升高可信来源占比并补充官方救援查询。",
            }
        )

    if any(item.get("entity_consistency_score", 1.0) < 0.9 for item in failure_analysis.get("failing_topics", [])):
        actions.append(
            {
                "action": "strengthen_entity_resolution",
                "reason": "存在实体漂移风险，需要加强 canonical entity 检测与冲突降级。",
            }
        )

    plan = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "round": round_index,
        "actions": actions or [{"action": "hold", "reason": "当前轮已达标，无需追加策略补丁。"}],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "strategy_patch_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return plan


def run_optimization(
    *,
    output_root: Path,
    max_rounds: int = 3,
    max_loops: int = 2,
    skip_judge: bool | None = None,
    research_profile: str = "benchmark",
) -> dict[str, Any]:
    """运行 local3 自动优化闭环。"""
    settings = get_settings()
    topics = load_topics(topic_set="local3")
    effective_skip_judge = skip_judge if skip_judge is not None else not bool(settings.get_llm_config().get("api_key"))

    completed_rounds = 0
    thresholds_met = False
    round_summaries: list[dict[str, Any]] = []

    for round_index in range(1, max_rounds + 1):
        round_dir = output_root / f"round-{round_index}"
        results = run_benchmark_suite(
            topics=topics,
            comparator_names=["ours"],
            output_root=round_dir,
            use_judge=not effective_skip_judge,
            max_loops=max_loops,
            research_profile=research_profile,
        )
        save_results(results, round_dir)
        summary = _normalize_summary_payload(build_benchmark_summary(results, comparator_name="ours"))
        save_summary(summary, round_dir)
        failure_analysis = build_failure_analysis(results=results, summary=summary, output_root=round_dir)
        build_strategy_patch_plan(
            summary=summary,
            failure_analysis=failure_analysis,
            output_root=round_dir,
            round_index=round_index,
        )
        round_summaries.append(
            {
                "round": round_index,
                "output_dir": str(round_dir),
                "summary": summary,
            }
        )
        completed_rounds = round_index
        thresholds_met = summary_meets_thresholds(summary)
        if thresholds_met:
            break

    outcome = {
        "completed_rounds": completed_rounds,
        "thresholds_met": thresholds_met,
        "rounds": round_summaries,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "optimization_summary.json").write_text(
        json.dumps(outcome, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return outcome


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="local3 benchmark 自动优化器")
    parser.add_argument("--output-dir", type=str, help="优化输出目录")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大优化轮数")
    parser.add_argument("--max-loops", type=int, default=2, help="单次 benchmark 的最大研究循环次数")
    parser.add_argument("--skip-judge", action="store_true", help="跳过 LLM Judge")
    parser.add_argument("--profile", type=str, default="benchmark", help="运行 profile")
    args = parser.parse_args()

    run_id = time.strftime("%Y%m%d-%H%M%S")
    output_root = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "workspace" / "benchmarks" / "optimization_runs" / run_id
    outcome = run_optimization(
        output_root=output_root,
        max_rounds=args.max_rounds,
        max_loops=args.max_loops,
        skip_judge=args.skip_judge,
        research_profile=args.profile,
    )
    logger.info("优化完成: rounds={}, thresholds_met={}", outcome["completed_rounds"], outcome["thresholds_met"])


if __name__ == "__main__":
    main()
