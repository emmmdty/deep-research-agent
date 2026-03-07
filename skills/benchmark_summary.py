"""Benchmark 总结技能——自动化整理和分析评测基准结果。"""

from __future__ import annotations

from loguru import logger

from workflows.graph import run_research


BENCHMARK_TOPIC_TEMPLATE = """\
请对以下主题进行 Benchmark/评测总结分析：
{topic}

重点关注：
1. 当前主流评测基准和数据集
2. 各方案在基准上的性能对比
3. 评测指标的意义和局限性
4. 最新 SOTA 结果
"""


def run_benchmark_summary(topic: str, max_loops: int = 3) -> str:
    """执行 Benchmark 总结技能。

    Args:
        topic: Benchmark 总结主题。
        max_loops: 最大研究迭代次数。

    Returns:
        Benchmark 总结 Markdown 报告。
    """
    logger.info("📊 启动 Benchmark 总结技能: topic='{}'", topic)
    enhanced_topic = BENCHMARK_TOPIC_TEMPLATE.format(topic=topic)
    result = run_research(enhanced_topic, max_loops=max_loops)
    return result.get("final_report", "Benchmark 总结生成失败")
