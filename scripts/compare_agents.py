"""离线报告对比脚本——对比两份已生成研究报告的质量。

使用方式：
    uv run python scripts/compare_agents.py --file-a workspace/our_report.md --file-b workspace/gptr_report.md
"""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from evaluation.metrics import evaluate_report
from evaluation.llm_judge import LLMJudge

console = Console()


def compare_from_files(file_a: str, file_b: str, topic: str = "") -> None:
    """从文件对比两份报告。"""
    report_a = Path(file_a).read_text(encoding="utf-8")
    report_b = Path(file_b).read_text(encoding="utf-8")
    _run_comparison(report_a, report_b, "Our Agent", "竞品", topic)


def _run_comparison(
    report_a: str, report_b: str,
    name_a: str, name_b: str, topic: str
) -> None:
    """执行对比评估并输出结果。"""
    # 基础指标
    metrics_a = evaluate_report(report_a)
    metrics_b = evaluate_report(report_b)

    # LLM Judge 盲评
    judge = LLMJudge()
    comparison = judge.compare_reports(report_a, report_b, topic)

    # 输出对比表
    table = Table(title=f"📊 竞品对比: {name_a} vs {name_b}", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column(name_a, justify="right")
    table.add_column(name_b, justify="right")
    table.add_column("胜出", justify="center")

    # 基础指标对比
    _add_comparison_row(table, "报告字数", metrics_a["word_count"], metrics_b["word_count"])
    _add_comparison_row(table, "标题数", metrics_a["heading_count"], metrics_b["heading_count"])
    _add_comparison_row(table, "引用来源数", metrics_a["source_coverage"], metrics_b["source_coverage"])
    _add_comparison_row(table, "引用准确率",
                        f"{metrics_a['citation_accuracy']:.0%}",
                        f"{metrics_b['citation_accuracy']:.0%}",
                        metrics_a["citation_accuracy"], metrics_b["citation_accuracy"])
    _add_comparison_row(table, "深度评分", metrics_a["depth_score"], metrics_b["depth_score"])

    # LLM Judge 对比
    scores_a = comparison["report_a"]
    scores_b = comparison["report_b"]
    for dim in ["depth", "accuracy", "coherence", "citation_quality", "structure", "overall"]:
        dim_label = {
            "depth": "Judge:深度", "accuracy": "Judge:准确度",
            "coherence": "Judge:连贯性", "citation_quality": "Judge:引用质量",
            "structure": "Judge:结构", "overall": "Judge:综合",
        }[dim]
        _add_comparison_row(table, dim_label,
                            scores_a.get(dim, 0), scores_b.get(dim, 0))

    console.print()
    console.print(table)

    # 胜负结论
    winner = comparison["winner"]
    winner_name = name_a if winner == "A" else (name_b if winner == "B" else "平局")
    diff = abs(comparison["score_diff"])
    console.print(Panel(
        f"🏆 综合胜出: [bold]{winner_name}[/bold]  (分差: {diff})",
        border_style="green" if winner == "A" else "yellow",
    ))


def _add_comparison_row(
    table: Table, label: str, val_a, val_b,
    num_a=None, num_b=None,
) -> None:
    """添加对比行。"""
    if num_a is None:
        try:
            num_a, num_b = float(val_a), float(val_b)
        except (ValueError, TypeError):
            num_a, num_b = 0, 0

    if num_a > num_b:
        winner = "A ✅"
    elif num_b > num_a:
        winner = "B ✅"
    else:
        winner = "="

    table.add_row(label, str(val_a), str(val_b), winner)


def _print_single_result(report: str, topic: str) -> None:
    """输出单一 Agent 的评估结果。"""
    metrics = evaluate_report(report)
    judge = LLMJudge()
    scores = judge.score_report(report, topic)

    table = Table(title="📊 Deep Research Agent 评估结果", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column("数值", justify="right")

    table.add_row("报告字数", str(metrics["word_count"]))
    table.add_row("引用来源", str(metrics["source_coverage"]))
    table.add_row("引用准确率", f"{metrics['citation_accuracy']:.0%}")
    table.add_row("深度评分", str(metrics["depth_score"]))
    table.add_row("Judge 综合", str(scores.get("overall", "-")))
    table.add_row("Judge 评语", str(scores.get("comments", "-"))[:80])

    console.print()
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Deep Research Agent 离线报告对比")
    parser.add_argument("--file-a", type=str, help="报告 A 文件路径")
    parser.add_argument("--file-b", type=str, help="报告 B 文件路径")
    args = parser.parse_args()

    if args.file_a and args.file_b:
        compare_from_files(args.file_a, args.file_b)
    else:
        parser.print_help()
    console.print("\n[yellow]示例:[/yellow]")
    console.print('  uv run python scripts/compare_agents.py --file-a a.md --file-b b.md')


if __name__ == "__main__":
    main()
