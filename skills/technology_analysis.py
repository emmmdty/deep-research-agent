"""技术分析技能——自动化执行技术方案分析。"""

from __future__ import annotations

from loguru import logger

from legacy.workflows.graph import run_research


TECH_ANALYSIS_TOPIC_TEMPLATE = """\
请对以下技术进行深度分析：
{topic}

重点关注：
1. 技术原理和架构设计
2. 与竞品/替代方案的对比分析
3. 优缺点分析
4. 适用场景和最佳实践
5. 生态系统和社区活跃度
"""


def run_technology_analysis(topic: str, max_loops: int = 3) -> str:
    """执行技术分析技能。

    Args:
        topic: 技术分析主题。
        max_loops: 最大研究迭代次数。

    Returns:
        技术分析 Markdown 报告。
    """
    logger.info("🔧 启动技术分析技能: topic='{}'", topic)
    enhanced_topic = TECH_ANALYSIS_TOPIC_TEMPLATE.format(topic=topic)
    result = run_research(enhanced_topic, max_loops=max_loops)
    return result.get("final_report", "技术分析报告生成失败")
