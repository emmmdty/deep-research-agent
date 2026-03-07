"""增强版 Benchmark 运行脚本——含 LLM-as-Judge 评分、成本追踪和竞品对比。

使用方式：
    # 基础评测（评测自身）
    uv run python scripts/run_benchmark.py

    # 与 GPT Researcher 对比
    uv run python scripts/run_benchmark.py --compare gpt-researcher

    # 指定测试主题数
    uv run python scripts/run_benchmark.py --max-topics 3

    # 跳过 LLM Judge（更快）
    uv run python scripts/run_benchmark.py --skip-judge
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from evaluation.metrics import evaluate_report
from evaluation.llm_judge import LLMJudge
from evaluation.cost_tracker import CostTracker
from workflows.graph import run_research

console = Console()


def load_topics(max_topics: int = 0) -> list[dict]:
    """加载标准评测主题。"""
    topics_file = Path(__file__).parent.parent / "evaluation" / "benchmarks" / "topics.json"
    with open(topics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    topics = data["topics"]
    if max_topics > 0:
        topics = topics[:max_topics]
    return topics


def run_single_benchmark(topic_data: dict, use_judge: bool = True) -> dict:
    """对单个主题执行完整评测。"""
    topic = topic_data["topic"]
    topic_id = topic_data["id"]
    expected_aspects = topic_data.get("expected_aspects", [])
    min_words = topic_data.get("min_words", 2000)
    min_sources = topic_data.get("min_sources", 5)

    console.print(f"\n[bold cyan]📝 [{topic_id}][/bold cyan] {topic}")

    # 成本追踪
    tracker = CostTracker()
    tracker.start()

    try:
        # 运行研究
        state = run_research(topic, max_loops=2)
        cost = tracker.stop()

        report = state.get("final_report", "")

        # 基础指标
        basic_metrics = evaluate_report(report)

        # 预期方面覆盖检查
        aspect_hits = 0
        for aspect in expected_aspects:
            # 检查报告中是否包含关键词
            keywords = aspect.split("/")
            if any(kw.strip() in report for kw in keywords):
                aspect_hits += 1
        aspect_coverage = aspect_hits / len(expected_aspects) if expected_aspects else 0

        # LLM-as-Judge 评分
        judge_scores = {}
        if use_judge:
            judge = LLMJudge()
            judge_scores = judge.score_report(report, topic)

        result = {
            "topic_id": topic_id,
            "topic": topic[:30],
            "status": "✅",
            # 基础指标
            **basic_metrics,
            # 扩展指标
            "aspect_coverage": round(aspect_coverage, 2),
            "meets_min_words": basic_metrics["word_count"] >= min_words,
            "meets_min_sources": basic_metrics["source_coverage"] >= min_sources,
            # LLM Judge 评分
            "judge_overall": judge_scores.get("overall", "-"),
            "judge_depth": judge_scores.get("depth", "-"),
            "judge_accuracy": judge_scores.get("accuracy", "-"),
            "judge_coherence": judge_scores.get("coherence", "-"),
            "judge_citation": judge_scores.get("citation_quality", "-"),
            "judge_structure": judge_scores.get("structure", "-"),
            "judge_comments": judge_scores.get("comments", ""),
            # 成本
            "time_seconds": cost.total_time_seconds,
            "llm_calls": cost.llm_calls,
            "search_calls": cost.search_calls,
            "total_tokens": cost.total_tokens,
        }

        console.print(
            f"  ✅ 完成: {basic_metrics['word_count']} 字, "
            f"来源={basic_metrics['source_coverage']}, "
            f"Judge={judge_scores.get('overall', 'N/A')}/10, "
            f"耗时={cost.total_time_seconds:.1f}s"
        )

        # 保存报告到 workspace
        _save_report(topic_id, topic, report)

        return result

    except Exception as e:
        tracker.stop()
        logger.error("评测失败: topic='{}', error={}", topic, e)
        console.print(f"  ❌ 失败: {e}")
        return {
            "topic_id": topic_id,
            "topic": topic[:30],
            "status": "❌",
            "error": str(e),
        }


def _save_report(topic_id: str, topic: str, report: str) -> None:
    """保存报告到 workspace。"""
    output_dir = Path(__file__).parent.parent / "workspace" / "benchmark_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{topic_id}_{topic[:15].replace(' ', '_')}.md"
    filepath.write_text(report, encoding="utf-8")


def print_results(results: list[dict], use_judge: bool = True) -> None:
    """输出评测结果汇总表。"""

    # 基础指标表
    table = Table(title="📊 Benchmark 基础指标", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("主题", style="cyan", max_width=25)
    table.add_column("状态", width=4)
    table.add_column("字数", justify="right")
    table.add_column("来源", justify="right")
    table.add_column("引用率", justify="right")
    table.add_column("方面覆盖", justify="right")
    table.add_column("深度分", justify="right")

    for r in results:
        if r.get("status") == "❌":
            table.add_row(
                r.get("topic_id", ""), r.get("topic", ""),
                "❌", "-", "-", "-", "-", "-",
            )
        else:
            table.add_row(
                r.get("topic_id", ""),
                r.get("topic", ""),
                "✅",
                str(r.get("word_count", 0)),
                str(r.get("source_coverage", 0)),
                f"{r.get('citation_accuracy', 0):.0%}",
                f"{r.get('aspect_coverage', 0):.0%}",
                f"{r.get('depth_score', 0):.2f}",
            )

    console.print()
    console.print(table)

    # LLM Judge 评分表
    if use_judge:
        judge_table = Table(title="🧑‍⚖️ LLM-as-Judge 评分", show_lines=True)
        judge_table.add_column("ID", style="dim", width=4)
        judge_table.add_column("主题", style="cyan", max_width=25)
        judge_table.add_column("综合", justify="right")
        judge_table.add_column("深度", justify="right")
        judge_table.add_column("准确度", justify="right")
        judge_table.add_column("连贯性", justify="right")
        judge_table.add_column("引用", justify="right")
        judge_table.add_column("结构", justify="right")

        for r in results:
            if r.get("status") == "❌":
                continue
            judge_table.add_row(
                r.get("topic_id", ""),
                r.get("topic", ""),
                str(r.get("judge_overall", "-")),
                str(r.get("judge_depth", "-")),
                str(r.get("judge_accuracy", "-")),
                str(r.get("judge_coherence", "-")),
                str(r.get("judge_citation", "-")),
                str(r.get("judge_structure", "-")),
            )

        console.print()
        console.print(judge_table)

    # 成本表
    cost_table = Table(title="💰 成本与性能", show_lines=True)
    cost_table.add_column("ID", style="dim", width=4)
    cost_table.add_column("主题", style="cyan", max_width=25)
    cost_table.add_column("耗时", justify="right")
    cost_table.add_column("LLM调用", justify="right")
    cost_table.add_column("搜索调用", justify="right")

    for r in results:
        if r.get("status") == "❌":
            continue
        cost_table.add_row(
            r.get("topic_id", ""),
            r.get("topic", ""),
            f"{r.get('time_seconds', 0):.1f}s",
            str(r.get("llm_calls", 0)),
            str(r.get("search_calls", 0)),
        )

    console.print()
    console.print(cost_table)

    # 汇总统计
    valid = [r for r in results if r.get("status") == "✅"]
    if valid:
        avg_words = sum(r.get("word_count", 0) for r in valid) / len(valid)
        avg_sources = sum(r.get("source_coverage", 0) for r in valid) / len(valid)
        avg_judge = [r.get("judge_overall", 0) for r in valid if isinstance(r.get("judge_overall"), (int, float))]
        avg_judge_score = sum(avg_judge) / len(avg_judge) if avg_judge else 0

        console.print()
        console.print(Panel(
            f"成功率: {len(valid)}/{len(results)}\n"
            f"平均字数: {avg_words:.0f}\n"
            f"平均来源: {avg_sources:.1f}\n"
            f"平均 Judge 评分: {avg_judge_score:.1f}/10",
            title="📈 汇总",
            border_style="green",
        ))

    # 保存 JSON 结果
    output_file = Path(__file__).parent.parent / "workspace" / "benchmark_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    console.print(f"\n📄 结果已保存: [cyan]{output_file}[/cyan]")


def main():
    parser = argparse.ArgumentParser(description="Deep Research Agent Benchmark")
    parser.add_argument("--max-topics", type=int, default=0, help="最大测试主题数（0=全部）")
    parser.add_argument("--skip-judge", action="store_true", help="跳过 LLM Judge 评分")
    parser.add_argument("--compare", type=str, help="竞品名称（如 gpt-researcher）")
    args = parser.parse_args()

    console.print(Panel(
        "[bold cyan]🔬 Deep Research Agent Benchmark v2.0[/bold cyan]",
        border_style="blue",
    ))

    topics = load_topics(args.max_topics)
    console.print(f"评测主题: {len(topics)} 个  |  LLM Judge: {'✅' if not args.skip_judge else '❌'}")

    results = []
    for topic_data in topics:
        result = run_single_benchmark(topic_data, use_judge=not args.skip_judge)
        results.append(result)

    print_results(results, use_judge=not args.skip_judge)


if __name__ == "__main__":
    main()
