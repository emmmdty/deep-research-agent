"""统一全量 comparator 对比脚本。"""

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
from evaluation.comparators import load_topics, resolve_comparators
from evaluation.llm_judge import LLMJudge
from scripts.run_benchmark import run_benchmark_suite

load_dotenv(PROJECT_ROOT / ".env")

console = Console()


def run_full_comparison_suite(
    *,
    comparator_names: list[str],
    max_topics: int = 0,
    output_root: Path,
    use_judge: bool = True,
    max_loops: int = 2,
) -> list[dict[str, Any]]:
    """运行全量 comparator 对比。"""
    topics = load_topics(max_topics=max_topics)
    results = run_benchmark_suite(
        topics=topics,
        comparator_names=comparator_names,
        output_root=output_root,
        use_judge=use_judge,
        max_loops=max_loops,
    )

    judge = LLMJudge() if use_judge else None
    for topic_result in results:
        pairwise: dict[str, Any] = {}
        ours = topic_result["comparators"].get("ours")
        for name, payload in topic_result["comparators"].items():
            if name == "ours":
                continue
            if not judge:
                pairwise[name] = {"status": "skipped", "reason": "judge disabled"}
                continue
            if not ours or not ours.get("success") or not payload.get("success"):
                pairwise[name] = {
                    "status": "skipped",
                    "reason": payload.get("error") or "missing successful report",
                }
                continue
            pairwise[name] = judge.compare_reports(
                ours.get("report_text", ""),
                payload.get("report_text", ""),
                topic_result["topic"],
            )
        topic_result["pairwise"] = pairwise
    return results


def generate_comparison_report(all_results: list[dict[str, Any]]) -> str:
    """生成 Markdown 对比报告。"""
    lines = [
        "# Full Comparator Comparison",
        "",
        f"> Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for topic_result in all_results:
        lines.extend(
            [
                f"## {topic_result['topic_id']} {topic_result['topic']}",
                "",
                "| Comparator | Status | Judge | Sources | Aspect | Notes |",
                "| --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for name, payload in topic_result["comparators"].items():
            metrics = payload.get("metrics", {})
            lines.append(
                f"| {name} | {payload.get('status', '-')} | {metrics.get('judge_overall', '-')} | "
                f"{metrics.get('source_coverage', '-')} | {metrics.get('aspect_coverage', '-')} | "
                f"{payload.get('error', '') or '-'} |"
            )

        pairwise = topic_result.get("pairwise", {})
        if pairwise:
            lines.extend(
                [
                    "",
                    "| Pairwise vs ours | Winner | Score Diff | Reason |",
                    "| --- | --- | ---: | --- |",
                ]
            )
            for name, payload in pairwise.items():
                lines.append(
                    f"| {name} | {payload.get('winner', payload.get('status', '-'))} | "
                    f"{payload.get('score_diff', '-')} | {payload.get('reason', '-') } |"
                )
        lines.append("")

    return "\n".join(lines)


def print_summary(all_results: list[dict[str, Any]]) -> None:
    """输出终端汇总表。"""
    table = Table(title="📊 Full Comparison 汇总", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Comparator", style="cyan", width=10)
    table.add_column("状态", width=10)
    table.add_column("Judge", justify="right")
    table.add_column("方面覆盖", justify="right")
    table.add_column("对 ours", justify="center")

    for topic_result in all_results:
        for name, payload in topic_result["comparators"].items():
            metrics = payload.get("metrics", {})
            pairwise = topic_result.get("pairwise", {}).get(name, {}) if name != "ours" else {}
            table.add_row(
                topic_result["topic_id"],
                name,
                payload.get("status", "-"),
                str(metrics.get("judge_overall", "-")),
                str(metrics.get("aspect_coverage", "-")),
                str(pairwise.get("winner", "-")) if name != "ours" else "-",
            )

    console.print()
    console.print(table)


def save_results(all_results: list[dict[str, Any]], output_root: Path) -> tuple[Path, Path]:
    """保存 Markdown 与 JSON 结果。"""
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "comparison_results.json"
    md_path = output_root / "comparison_report.md"
    json_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    md_path.write_text(generate_comparison_report(all_results), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="统一 comparator 全量对比")
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
    run_id = time.strftime("%Y%m%d-%H%M%S")
    output_root = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "workspace" / "comparisons" / run_id

    console.print(
        Panel(
            f"[bold cyan]Full Comparison[/bold cyan]\nComparators: {', '.join(comparator_names)}",
            border_style="blue",
        )
    )

    results = run_full_comparison_suite(
        comparator_names=comparator_names,
        max_topics=args.max_topics,
        output_root=output_root,
        use_judge=not args.skip_judge,
        max_loops=args.max_loops,
    )
    print_summary(results)
    json_path, md_path = save_results(results, output_root)
    console.print(f"\n📊 JSON: [cyan]{json_path}[/cyan]")
    console.print(f"📄 Markdown: [cyan]{md_path}[/cyan]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI 保护
        logger.exception("full comparison 运行失败: {}", exc)
        raise
