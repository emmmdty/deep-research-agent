"""Benchmark 运行脚本——批量测试并评估研究报告质量。

使用方式：
    uv run python scripts/run_benchmark.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from loguru import logger
from rich.console import Console
from rich.table import Table

from evaluation.metrics import evaluate_report
from workflows.graph import run_research

console = Console()

# 预定义的测试主题
BENCHMARK_TOPICS = [
    "2024年大语言模型Agent架构的最新进展",
    "RAG（检索增强生成）技术的原理和应用",
    "多模态大模型的发展现状与趋势",
]


def run_benchmark() -> None:
    """运行 Benchmark 并输出评估结果。"""
    console.print("[bold cyan]🔬 Deep Research Agent Benchmark[/bold cyan]\n")

    results = []

    for i, topic in enumerate(BENCHMARK_TOPICS, 1):
        console.print(f"[bold]📝 测试 {i}/{len(BENCHMARK_TOPICS)}:[/bold] {topic}")

        try:
            state = run_research(topic, max_loops=2)
            report = state.get("final_report", "")

            metrics = evaluate_report(report)
            metrics["topic"] = topic[:30]
            metrics["status"] = "✅"
            results.append(metrics)

            console.print(f"  ✅ 完成: {metrics['word_count']} 字\n")

        except Exception as e:
            logger.error("测试失败: topic='{}', error={}", topic, e)
            results.append({
                "topic": topic[:30],
                "status": "❌",
                "citation_accuracy": 0,
                "source_coverage": 0,
                "word_count": 0,
                "heading_count": 0,
                "paragraph_count": 0,
                "depth_score": 0,
            })
            console.print(f"  ❌ 失败: {e}\n")

    # 输出汇总表
    _print_results_table(results)


def _print_results_table(results: list[dict]) -> None:
    """输出评估结果汇总表。"""
    table = Table(title="📊 Benchmark 评估结果", show_lines=True)
    table.add_column("主题", style="cyan", max_width=30)
    table.add_column("状态")
    table.add_column("字数", justify="right")
    table.add_column("标题数", justify="right")
    table.add_column("引用准确率", justify="right")
    table.add_column("来源数", justify="right")
    table.add_column("深度评分", justify="right")

    for r in results:
        table.add_row(
            r.get("topic", ""),
            r.get("status", ""),
            str(r.get("word_count", 0)),
            str(r.get("heading_count", 0)),
            f"{r.get('citation_accuracy', 0):.1%}",
            str(r.get("source_coverage", 0)),
            f"{r.get('depth_score', 0):.2f}",
        )

    console.print()
    console.print(table)


if __name__ == "__main__":
    run_benchmark()
