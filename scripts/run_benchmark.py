"""统一 benchmark 运行脚本。"""

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
            result = run_comparator(name=name, topic=topic, output_root=output_root, max_loops=max_loops)
            payload = result.model_dump()

            if result.success and result.report_text:
                metrics = build_report_metrics(
                    report_text=result.report_text,
                    topic=topic,
                    runtime_metrics=result.metrics,
                    sources=result.sources,
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
    table.add_column("字数", justify="right")
    table.add_column("来源", justify="right")
    table.add_column("方面覆盖", justify="right")
    table.add_column("Judge", justify="right")
    table.add_column("耗时", justify="right")

    for topic_result in results:
        for name, payload in topic_result["comparators"].items():
            metrics = payload.get("metrics", {})
            table.add_row(
                topic_result["topic_id"],
                name,
                payload.get("status", "-"),
                str(metrics.get("word_count", "-")) if payload.get("success") else "-",
                str(metrics.get("source_coverage", "-")) if payload.get("success") else "-",
                str(metrics.get("aspect_coverage", "-")) if payload.get("success") else "-",
                str(metrics.get("judge_overall", "-")),
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


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="统一 benchmark 运行器")
    parser.add_argument("--comparators", type=str, help="逗号分隔的 comparator 列表")
    parser.add_argument("--include-optional", type=str, help="附加可选 comparator 列表")
    parser.add_argument("--max-topics", type=int, default=0, help="最大主题数（0 表示全部）")
    parser.add_argument("--skip-judge", action="store_true", help="跳过 LLM Judge")
    parser.add_argument("--max-loops", type=int, default=2, help="自身工作流最大循环次数")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    args = parser.parse_args()

    settings = get_settings()
    requested = [item.strip() for item in args.comparators.split(",")] if args.comparators else None
    optional = [item.strip() for item in args.include_optional.split(",")] if args.include_optional else None
    comparator_names = resolve_comparators(settings, requested=requested, include_optional=optional)
    topics = load_topics(max_topics=args.max_topics)
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
    )
    print_results(results)
    json_path, md_path = save_results(results, output_root)
    console.print(f"\n📊 JSON: [cyan]{json_path}[/cyan]")
    console.print(f"📄 Markdown: [cyan]{md_path}[/cyan]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI 保护
        logger.exception("benchmark 运行失败: {}", exc)
        raise
