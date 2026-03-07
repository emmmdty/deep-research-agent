"""文献综述技能——自动化执行学术文献综述流程。"""

from __future__ import annotations

from loguru import logger

from workflows.graph import run_research


LITERATURE_REVIEW_TOPIC_TEMPLATE = """\
请对以下主题进行学术文献综述：
{topic}

重点关注：
1. 近 2 年的核心论文和研究进展
2. 主要研究方法和技术路线
3. 存在的挑战和未解决的问题
4. 未来研究方向
"""


def run_literature_review(topic: str, max_loops: int = 3) -> str:
    """执行文献综述技能。

    Args:
        topic: 文献综述主题。
        max_loops: 最大研究迭代次数。

    Returns:
        文献综述 Markdown 报告。
    """
    logger.info("📖 启动文献综述技能: topic='{}'", topic)
    enhanced_topic = LITERATURE_REVIEW_TOPIC_TEMPLATE.format(topic=topic)
    result = run_research(enhanced_topic, max_loops=max_loops)
    return result.get("final_report", "文献综述生成失败")
