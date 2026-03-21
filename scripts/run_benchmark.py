"""统一 benchmark 运行脚本。"""

from __future__ import annotations

import argparse
import inspect
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from configs.settings import PROJECT_ROOT, get_settings
from evaluation.comparators import (
    BenchmarkTopic,
    build_report_metrics,
    load_topics,
    resolve_comparators,
    run_comparator,
)
from evaluation.llm_judge import LLMJudge

load_dotenv(PROJECT_ROOT / ".env")

console = Console()


def run_benchmark_suite(
    *,
    topics: list[BenchmarkTopic],
    comparator_names: list[str],
    output_root: Path,
    use_judge: bool = True,
    max_loops: int = 2,
    research_profile: str = "benchmark",
) -> list[dict[str, Any]]:
    """运行多主题 benchmark。"""
    judge = LLMJudge() if use_judge else None
    results: list[dict[str, Any]] = []

    for topic in topics:
        topic_result: dict[str, Any] = {
            "topic_id": topic.id,
            "topic": topic.topic,
            "comparators": {},
        }

        for name in comparator_names:
            signature = inspect.signature(run_comparator)
            kwargs = {
                "name": name,
                "topic": topic,
                "output_root": output_root,
                "max_loops": max_loops,
            }
            if "research_profile" in signature.parameters:
                kwargs["research_profile"] = research_profile
            result = run_comparator(**kwargs)
            payload = result.model_dump(exclude={"report_artifact"})

            if result.success and result.report_text:
                metrics = build_report_metrics(
                    report_text=result.report_text,
                    topic=topic,
                    runtime_metrics=result.metrics,
                    sources=result.sources,
                    report_artifact=result.report_artifact,
                )
                if judge is not None:
                    scores = judge.score_report(result.report_text, topic.topic)
                    metrics.update(
                        {
                            "judge_overall": scores.get("overall"),
                            "judge_depth": scores.get("depth"),
                            "judge_accuracy": scores.get("accuracy"),
                            "judge_coherence": scores.get("coherence"),
                            "judge_citation": scores.get("citation_quality"),
                            "judge_structure": scores.get("structure"),
                        }
                    )
                    payload["judge"] = scores
                payload["metrics"] = metrics
            else:
                payload.setdefault("metrics", result.metrics or {})
                payload["judge"] = {}

            topic_result["comparators"][name] = payload
        results.append(topic_result)

    return results


def generate_benchmark_markdown(results: list[dict[str, Any]]) -> str:
    """生成 benchmark Markdown 汇总。"""
    lines = [
        "# Benchmark Results",
        "",
        f"> Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Topic | Comparator | Status | Words | Sources | Aspect | Judge | Time |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for topic_result in results:
        for name, payload in topic_result["comparators"].items():
            metrics = payload.get("metrics", {})
            lines.append(
                f"| {topic_result['topic_id']} | {name} | {payload.get('status', '-')} | "
                f"{metrics.get('word_count', '-')} | {metrics.get('source_coverage', '-')} | "
                f"{metrics.get('aspect_coverage', '-')} | {metrics.get('judge_overall', '-')} | "
                f"{metrics.get('time_seconds', '-')} |"
            )
    return "\n".join(lines)


def print_results(results: list[dict[str, Any]]) -> None:
    """输出终端结果表。"""
    table = Table(title="📊 Benchmark 汇总", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Comparator", style="cyan", width=10)
    table.add_column("状态", width=10)
    table.add_column("可靠性", justify="right")
    table.add_column("控制力", justify="right")
    table.add_column("报告质量", justify="right")
    table.add_column("Gate", justify="right")
    table.add_column("耗时", justify="right")

    for topic_result in results:
        for name, payload in topic_result["comparators"].items():
            metrics = payload.get("metrics", {})
            table.add_row(
                topic_result["topic_id"],
                name,
                payload.get("status", "-"),
                _format_md_metric(metrics.get("research_reliability_score_100")) if payload.get("success") else "-",
                _format_md_metric(metrics.get("system_controllability_score_100")) if payload.get("success") else "-",
                _format_md_metric(metrics.get("report_quality_score_100")) if payload.get("success") else "-",
                _format_md_metric(metrics.get("quality_gate_margin_100")) if payload.get("success") else "-",
                str(metrics.get("time_seconds", "-")),
            )

    console.print()
    console.print(table)


def save_results(results: list[dict[str, Any]], output_root: Path) -> tuple[Path, Path]:
    """保存 JSON 与 Markdown 结果。"""
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "benchmark_results.json"
    md_path = output_root / "benchmark_results.md"

    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    md_path.write_text(generate_benchmark_markdown(results), encoding="utf-8")
    return json_path, md_path


def build_benchmark_summary(
    results: list[dict[str, Any]],
    *,
    comparator_name: str = "ours",
) -> dict[str, Any]:
    """生成聚合 benchmark summary。"""
    rows: list[dict[str, Any]] = []
    for topic_result in results:
        payload = topic_result["comparators"].get(comparator_name, {})
        metrics = payload.get("metrics", {})
        time_seconds = float(metrics.get("time_seconds", 0.0) or 0.0)
        quality_gate_passed = bool(metrics.get("quality_gate_passed", False))
        rows.append(
            {
                "topic_id": topic_result["topic_id"],
                "topic": topic_result["topic"],
                "status": payload.get("status", "-"),
                "success": bool(payload.get("success")),
                "word_count": metrics.get("word_count", 0) or 0,
                "source_coverage": metrics.get("source_coverage", 0) or 0,
                "aspect_coverage": metrics.get("aspect_coverage", 0.0) or 0.0,
                "citation_accuracy": metrics.get("citation_accuracy", 0.0) or 0.0,
                "depth_score": metrics.get("depth_score", 0.0) or 0.0,
                "time_seconds": time_seconds,
                "tool_use_success_rate": metrics.get("tool_use_success_rate"),
                "judge_overall": metrics.get("judge_overall"),
                "judge_accuracy": metrics.get("judge_accuracy"),
                "judge_citation": metrics.get("judge_citation"),
                "quality_gate_passed": quality_gate_passed,
                "high_trust_aspect_score_100": metrics.get("high_trust_aspect_score_100"),
                "cross_source_corroboration_score_100": metrics.get("cross_source_corroboration_score_100"),
                "verification_strength_score_100": metrics.get("verification_strength_score_100"),
                "entity_resolution_score_100": metrics.get("entity_resolution_score_100"),
                "citation_alignment_score_100": metrics.get("citation_alignment_score_100"),
                "conflict_disclosure_score_100": metrics.get("conflict_disclosure_score_100"),
                "quality_gate_margin_100": metrics.get("quality_gate_margin_100"),
                "coverage_balance_score_100": metrics.get("coverage_balance_score_100"),
                "structure_completeness_score_100": metrics.get("structure_completeness_score_100"),
                "evidence_novelty_score_100": metrics.get("evidence_novelty_score_100"),
                "support_specificity_score_100": metrics.get("support_specificity_score_100"),
                "recovery_resilience_score_100": metrics.get("recovery_resilience_score_100"),
                "research_reliability_score_100": metrics.get("research_reliability_score_100"),
                "system_controllability_score_100": metrics.get("system_controllability_score_100"),
                "report_quality_score_100": metrics.get("report_quality_score_100"),
                "evaluation_reproducibility_score_100": _evaluation_reproducibility_score(
                    status=payload.get("status", "-"),
                    quality_gate_passed=quality_gate_passed,
                    time_seconds=time_seconds,
                ),
            }
        )

    completed_rows = [row for row in rows if row["status"] == "completed"]

    def _stats(metric: str) -> dict[str, Any]:
        values = [row[metric] for row in completed_rows if row.get(metric) is not None]
        if not values:
            return {"avg": None, "median": None, "min": None, "max": None}
        return {
            "avg": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
        }

    judge_status = "scored" if any(row.get("judge_overall") is not None for row in completed_rows) else "skipped"
    rankings = {
        "by_research_reliability_score_100": [
            row["topic_id"]
            for row in sorted(
                completed_rows,
                key=lambda row: row.get("research_reliability_score_100") or 0.0,
                reverse=True,
            )
        ],
        "by_system_controllability_score_100": [
            row["topic_id"]
            for row in sorted(
                completed_rows,
                key=lambda row: row.get("system_controllability_score_100") or 0.0,
                reverse=True,
            )
        ],
        "by_report_quality_score_100": [
            row["topic_id"]
            for row in sorted(
                completed_rows,
                key=lambda row: row.get("report_quality_score_100") or 0.0,
                reverse=True,
            )
        ],
        "by_time_seconds_fastest": [
            row["topic_id"]
            for row in sorted(completed_rows, key=lambda row: row["time_seconds"])
        ],
    }
    if judge_status == "scored":
        rankings["by_judge_overall"] = [
            row["topic_id"]
            for row in sorted(
                completed_rows,
                key=lambda row: row.get("judge_overall") or 0.0,
                reverse=True,
            )
        ]

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "comparator": comparator_name,
        "judge_status": judge_status,
        "results": rows,
        "counts": {
            "completed": sum(1 for row in rows if row["status"] == "completed"),
            "failed": sum(1 for row in rows if row["status"] != "completed"),
            "quality_gate_passed": sum(1 for row in rows if row["quality_gate_passed"]),
        },
        "aggregates": {
            metric: _stats(metric)
            for metric in [
                "high_trust_aspect_score_100",
                "cross_source_corroboration_score_100",
                "verification_strength_score_100",
                "entity_resolution_score_100",
                "citation_alignment_score_100",
                "conflict_disclosure_score_100",
                "quality_gate_margin_100",
                "coverage_balance_score_100",
                "structure_completeness_score_100",
                "research_reliability_score_100",
                "system_controllability_score_100",
                "report_quality_score_100",
                "evaluation_reproducibility_score_100",
                "evidence_novelty_score_100",
                "support_specificity_score_100",
                "recovery_resilience_score_100",
                "time_seconds",
            ]
        },
        "scorecard": {
            metric: _stats(metric)
            for metric in [
                "research_reliability_score_100",
                "system_controllability_score_100",
                "report_quality_score_100",
                "evaluation_reproducibility_score_100",
            ]
        },
        "legacy_metrics": {
            metric: _stats(metric)
            for metric in [
                "word_count",
                "source_coverage",
                "aspect_coverage",
                "citation_accuracy",
                "depth_score",
                "judge_overall",
                "judge_accuracy",
                "judge_citation",
            ]
        },
        "benchmark_health": {
            "judge_status": judge_status,
            "completion_rate_100": round(
                100 * (sum(1 for row in rows if row["status"] == "completed") / len(rows)),
                3,
            )
            if rows
            else 0.0,
            "quality_gate_pass_rate_100": round(
                100 * (sum(1 for row in rows if row["quality_gate_passed"]) / len(rows)),
                3,
            )
            if rows
            else 0.0,
            "avg_tool_use_success_rate": _stats_from_metrics(completed_rows, "tool_use_success_rate"),
            "avg_recovery_resilience_score_100": _stats_from_metrics(
                completed_rows,
                "recovery_resilience_score_100",
            ),
        },
        "rankings": rankings,
    }


def _summary_to_markdown(summary: dict[str, Any]) -> str:
    """把 summary 转成 Markdown。"""
    lines = [
        "# Benchmark Summary",
        "",
        f"- Generated At: `{summary['generated_at']}`",
        f"- Comparator: `{summary['comparator']}`",
        f"- Judge Status: `{summary.get('judge_status', 'unknown')}`",
        "",
        "## Result Table",
        "",
        "| Topic ID | Topic | Status | Reliability | Control | Report Quality | Reproducibility | High-Trust Aspect | Verification | Citation Align | Gate Margin |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["results"]:
        lines.append(
            f"| {row['topic_id']} | {row['topic']} | {row['status']} | "
            f"{_format_md_metric(row.get('research_reliability_score_100'))} | "
            f"{_format_md_metric(row.get('system_controllability_score_100'))} | "
            f"{_format_md_metric(row.get('report_quality_score_100'))} | "
            f"{_format_md_metric(row.get('evaluation_reproducibility_score_100'))} | "
            f"{_format_md_metric(row.get('high_trust_aspect_score_100'))} | "
            f"{_format_md_metric(row.get('verification_strength_score_100'))} | "
            f"{_format_md_metric(row.get('citation_alignment_score_100'))} | "
            f"{_format_md_metric(row.get('quality_gate_margin_100'))} |"
        )

    lines.extend(["", "## Scorecard", ""])
    for key, value in summary.get("scorecard", {}).items():
        lines.append(f"- {key}: avg={_format_md_metric(value.get('avg'))}, min={_format_md_metric(value.get('min'))}, max={_format_md_metric(value.get('max'))}")

    lines.extend(["", "## Legacy Metrics", ""])
    for key, value in summary.get("legacy_metrics", {}).items():
        lines.append(f"- {key}: avg={_format_md_metric(value.get('avg'))}, min={_format_md_metric(value.get('min'))}, max={_format_md_metric(value.get('max'))}")

    lines.extend(["", "## Counts", ""])
    for key, value in summary["counts"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Benchmark Health", ""])
    for key, value in summary.get("benchmark_health", {}).items():
        if isinstance(value, dict):
            lines.append(
                f"- {key}: avg={_format_md_metric(value.get('avg'))}, min={_format_md_metric(value.get('min'))}, max={_format_md_metric(value.get('max'))}"
            )
        else:
            lines.append(f"- {key}: {_format_md_metric(value)}")

    lines.extend(["", "## Rankings", ""])
    for key, value in summary["rankings"].items():
        lines.append(f"- {key}: {', '.join(value) if value else 'none'}")
    return "\n".join(lines)


def _evaluation_reproducibility_score(*, status: str, quality_gate_passed: bool, time_seconds: float) -> float:
    completion_component = 1.0 if status == "completed" else 0.0
    gate_component = 1.0 if quality_gate_passed else 0.0
    runtime_component = max(0.0, 1.0 - min(time_seconds / 180.0, 1.0))
    return round(100 * (0.45 * completion_component + 0.35 * gate_component + 0.20 * runtime_component), 3)


def _format_md_metric(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _stats_from_metrics(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    values = [row[metric] for row in rows if row.get(metric) is not None]
    if not values:
        return {"avg": None, "median": None, "min": None, "max": None}
    return {
        "avg": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def save_summary(summary: dict[str, Any], output_root: Path) -> tuple[Path, Path]:
    """保存 summary JSON 和 Markdown。"""
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "benchmark_summary.json"
    md_path = output_root / "benchmark_summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_summary_to_markdown(summary), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="统一 benchmark 运行器")
    parser.add_argument("--comparators", type=str, help="逗号分隔的 comparator 列表")
    parser.add_argument("--include-optional", type=str, help="附加可选 comparator 列表")
    parser.add_argument("--max-topics", type=int, default=0, help="最大主题数（0 表示全部）")
    parser.add_argument("--skip-judge", action="store_true", help="跳过 LLM Judge")
    parser.add_argument("--max-loops", type=int, default=2, help="自身工作流最大循环次数")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--topic-set", type=str, default="default", help="主题集：default / local3 / portfolio12")
    parser.add_argument("--summary", action="store_true", help="生成聚合 summary 文件")
    parser.add_argument("--profile", type=str, default="benchmark", help="运行 profile：default 或 benchmark")
    args = parser.parse_args()

    settings = get_settings()
    requested = [item.strip() for item in args.comparators.split(",")] if args.comparators else None
    optional = [item.strip() for item in args.include_optional.split(",")] if args.include_optional else None
    comparator_names = resolve_comparators(settings, requested=requested, include_optional=optional)
    topics = load_topics(max_topics=args.max_topics, topic_set=args.topic_set)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    output_root = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "workspace" / "benchmarks" / run_id

    console.print(
        Panel(
            f"[bold cyan]Benchmark[/bold cyan]\nComparators: {', '.join(comparator_names)}\nTopics: {len(topics)}",
            border_style="blue",
        )
    )

    results = run_benchmark_suite(
        topics=topics,
        comparator_names=comparator_names,
        output_root=output_root,
        use_judge=not args.skip_judge,
        max_loops=args.max_loops,
        research_profile=args.profile,
    )
    print_results(results)
    json_path, md_path = save_results(results, output_root)
    summary_paths = None
    if args.summary:
        summary_paths = save_summary(build_benchmark_summary(results), output_root)
    console.print(f"\n📊 JSON: [cyan]{json_path}[/cyan]")
    console.print(f"📄 Markdown: [cyan]{md_path}[/cyan]")
    if summary_paths is not None:
        console.print(f"🧾 Summary JSON: [cyan]{summary_paths[0]}[/cyan]")
        console.print(f"🧾 Summary Markdown: [cyan]{summary_paths[1]}[/cyan]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI 保护
        logger.exception("benchmark 运行失败: {}", exc)
        raise
