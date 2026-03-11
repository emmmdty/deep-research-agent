"""基础研究示例——演示如何使用 Deep Research Agent。

使用方式：
    uv run python examples/basic_research.py
"""
# ruff: noqa: E402

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from workflows.graph import run_research
from evaluation.metrics import evaluate_report
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def main():
    """运行一个基础研究示例。"""
    topic = "2024年大语言模型Agent架构的最新进展"

    console.print(f"[bold cyan]🔬 研究主题:[/bold cyan] {topic}\n")

    # 运行研究
    result = run_research(topic, max_loops=2)

    # 输出报告
    report = result.get("final_report", "报告生成失败")
    console.print(Markdown(report))

    # 评估
    console.print("\n[bold cyan]📊 报告评估:[/bold cyan]")
    metrics = evaluate_report(report)
    for key, value in metrics.items():
        console.print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
