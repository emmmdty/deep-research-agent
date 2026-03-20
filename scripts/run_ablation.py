"""运行内部 ablation 对照实验。"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from configs.settings import PROJECT_ROOT, get_settings
from evaluation.comparators import build_report_metrics, load_topics, run_comparator

load_dotenv(PROJECT_ROOT / ".env")

ABLATION_VARIANTS = ["ours_base", "ours_verifier", "ours_gate", "ours_full"]


def run_ablation(
    *,
    output_root: Path,
    topic_set: str = "portfolio12",
    max_topics: int = 0,
    max_loops: int = 2,
    use_judge: bool = False,
    research_profile: str = "benchmark",
) -> dict[str, Any]:
    """运行内部 ablation 变体并写出结果文件。"""
    del use_judge  # 该脚本当前聚焦结构化指标，不单独接 LLM judge。

    settings = get_settings()
    topics = load_topics(topic_set=topic_set, max_topics=max_topics)
    output_root.mkdir(parents=True, exist_ok=True)

    topic_payloads: list[dict[str, Any]] = []
    for topic in topics:
        topic_result: dict[str, Any] = {
            "topic_id": topic.id,
            "topic": topic.topic,
            "comparators": {},
        }
        for variant in ABLATION_VARIANTS:
            result = run_comparator(
                name=variant,
                topic=topic,
                output_root=output_root,
                max_loops=max_loops,
                research_profile=research_profile,
                settings=settings,
                ablation_variant=variant,
            )
            payload = result.model_dump(exclude={"report_artifact"})
            metrics = dict(payload.get("metrics", {}) or {})
            needs_report_metrics = any(
                metrics.get(key) is None
                for key in (
                    "research_reliability_score_100",
                    "system_controllability_score_100",
                    "report_quality_score_100",
                )
            )
            if result.success and result.report_text and needs_report_metrics:
                payload["metrics"] = build_report_metrics(
                    report_text=result.report_text,
                    topic=topic,
                    runtime_metrics=result.metrics,
                    sources=result.sources,
                    report_artifact=result.report_artifact,
                )
            topic_result["comparators"][variant] = payload
        topic_payloads.append(topic_result)

    summary = _build_ablation_summary(topic_payloads)
    comparison_rows = _build_variant_comparison_rows(topic_payloads)

    (output_root / "ablation_results.json").write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "topic_set": topic_set,
                "variants": ABLATION_VARIANTS,
                "topics": topic_payloads,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_root / "ablation_summary.md").write_text(
        _summary_to_markdown(summary),
        encoding="utf-8",
    )
    _write_variant_csv(output_root / "variant_comparison.csv", comparison_rows)

    return {
        "variants": ABLATION_VARIANTS,
        "topics": topic_payloads,
        "summary": summary,
    }


def _build_ablation_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    per_variant: dict[str, list[dict[str, Any]]] = {variant: [] for variant in ABLATION_VARIANTS}
    for topic in results:
        for variant, payload in topic["comparators"].items():
            metrics = payload.get("metrics", {})
            per_variant[variant].append(
                {
                    "topic_id": topic["topic_id"],
                    "status": payload.get("status"),
                    "research_reliability_score_100": metrics.get("research_reliability_score_100"),
                    "system_controllability_score_100": metrics.get("system_controllability_score_100"),
                    "report_quality_score_100": metrics.get("report_quality_score_100"),
                    "quality_gate_passed": bool(metrics.get("quality_gate_passed")),
                    "time_seconds": metrics.get("time_seconds"),
                }
            )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "variants": {
            variant: {
                "completed": sum(1 for row in rows if row["status"] == "completed"),
                "quality_gate_pass_rate": _ratio(
                    sum(1 for row in rows if row["quality_gate_passed"]),
                    len(rows),
                ),
                "research_reliability_score_100": _stats(rows, "research_reliability_score_100"),
                "system_controllability_score_100": _stats(rows, "system_controllability_score_100"),
                "report_quality_score_100": _stats(rows, "report_quality_score_100"),
                "mean_time_seconds": _stats(rows, "time_seconds"),
            }
            for variant, rows in per_variant.items()
        },
    }


def _build_variant_comparison_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic in results:
        for variant, payload in topic["comparators"].items():
            metrics = payload.get("metrics", {})
            rows.append(
                {
                    "topic_id": topic["topic_id"],
                    "topic": topic["topic"],
                    "variant": variant,
                    "status": payload.get("status"),
                    "research_reliability_score_100": metrics.get("research_reliability_score_100"),
                    "system_controllability_score_100": metrics.get("system_controllability_score_100"),
                    "report_quality_score_100": metrics.get("report_quality_score_100"),
                    "quality_gate_passed": metrics.get("quality_gate_passed"),
                    "time_seconds": metrics.get("time_seconds"),
                }
            )
    return rows


def _summary_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Ablation Summary",
        "",
        f"- Generated At: `{summary['generated_at']}`",
        "",
        "| Variant | Completed | Gate Pass Rate | Reliability Avg | Control Avg | Report Quality Avg | Mean Time |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in ABLATION_VARIANTS:
        payload = summary["variants"][variant]
        lines.append(
            f"| {variant} | {payload['completed']} | {_format_metric(payload['quality_gate_pass_rate'])} | "
            f"{_format_metric(payload['research_reliability_score_100'].get('avg'))} | "
            f"{_format_metric(payload['system_controllability_score_100'].get('avg'))} | "
            f"{_format_metric(payload['report_quality_score_100'].get('avg'))} | "
            f"{_format_metric(payload['mean_time_seconds'].get('avg'))} |"
        )
    return "\n".join(lines)


def _write_variant_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "topic_id",
        "topic",
        "variant",
        "status",
        "research_reliability_score_100",
        "system_controllability_score_100",
        "report_quality_score_100",
        "quality_gate_passed",
        "time_seconds",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _stats(rows: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    if not values:
        return {"avg": None, "min": None, "max": None}
    return {
        "avg": round(statistics.mean(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def _format_metric(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="运行内部 ablation 变体对照实验")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--topic-set", type=str, default="portfolio12", help="主题集：portfolio12 或 local3")
    parser.add_argument("--max-topics", type=int, default=0, help="最多运行多少个主题")
    parser.add_argument("--max-loops", type=int, default=2, help="最大研究循环次数")
    parser.add_argument("--profile", type=str, default="benchmark", help="运行 profile")
    args = parser.parse_args()

    run_id = time.strftime("%Y%m%d-%H%M%S")
    output_root = (
        Path(args.output_dir)
        if args.output_dir
        else PROJECT_ROOT / "workspace" / "ablations" / run_id
    )
    outcome = run_ablation(
        output_root=output_root,
        topic_set=args.topic_set,
        max_topics=args.max_topics,
        max_loops=args.max_loops,
        research_profile=args.profile,
    )
    logger.info(
        "ablation 完成: variants={}, output={}",
        ",".join(outcome["variants"]),
        output_root,
    )


if __name__ == "__main__":
    main()
