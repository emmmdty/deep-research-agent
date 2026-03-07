"""研究报告质量评估指标。

指标：
    - citation_accuracy: 引用准确率（报告中引用标记的覆盖度）
    - source_coverage: 来源覆盖率（引用的唯一来源数量）
    - report_depth: 报告深度（字数、结构完整性）
"""

from __future__ import annotations

import re

from loguru import logger


def citation_accuracy(report: str) -> float:
    """计算引用准确率——报告中标注引用的段落占比。

    评估方式：检查报告中是否包含 [1]、[2] 等引用标记。

    Returns:
        0.0~1.0 的得分。
    """
    if not report:
        return 0.0

    paragraphs = [p.strip() for p in report.split("\n\n") if p.strip() and not p.startswith("#")]
    if not paragraphs:
        return 0.0

    cited_count = sum(1 for p in paragraphs if re.search(r"\[\d+\]", p))
    score = cited_count / len(paragraphs) if paragraphs else 0.0
    return round(min(score, 1.0), 3)


def source_coverage(report: str) -> int:
    """计算来源覆盖率——报告中引用的唯一来源数量。

    Returns:
        唯一引用编号的数量。
    """
    if not report:
        return 0

    citations = set(re.findall(r"\[(\d+)\]", report))
    return len(citations)


def report_depth(report: str) -> dict:
    """评估报告深度——字数、标题数、段落数。

    Returns:
        包含 word_count, heading_count, paragraph_count, depth_score 的字典。
    """
    if not report:
        return {"word_count": 0, "heading_count": 0, "paragraph_count": 0, "depth_score": 0.0}

    word_count = len(report)
    headings = re.findall(r"^#{1,4}\s+.+", report, re.MULTILINE)
    paragraphs = [p.strip() for p in report.split("\n\n") if p.strip()]

    # 深度评分：综合字数、标题数、段落数
    score = 0.0
    if word_count >= 5000:
        score += 0.4
    elif word_count >= 2000:
        score += 0.3
    elif word_count >= 1000:
        score += 0.2
    else:
        score += 0.1

    if len(headings) >= 5:
        score += 0.3
    elif len(headings) >= 3:
        score += 0.2
    else:
        score += 0.1

    if len(paragraphs) >= 10:
        score += 0.3
    elif len(paragraphs) >= 5:
        score += 0.2
    else:
        score += 0.1

    return {
        "word_count": word_count,
        "heading_count": len(headings),
        "paragraph_count": len(paragraphs),
        "depth_score": round(score, 2),
    }


def evaluate_report(report: str) -> dict:
    """综合评估研究报告质量。

    Returns:
        包含所有指标的评估结果字典。
    """
    cit_acc = citation_accuracy(report)
    src_cov = source_coverage(report)
    depth = report_depth(report)

    result = {
        "citation_accuracy": cit_acc,
        "source_coverage": src_cov,
        **depth,
    }

    logger.info(
        "📊 评估结果: citation_accuracy={}, source_coverage={}, "
        "word_count={}, depth_score={}",
        cit_acc, src_cov, depth["word_count"], depth["depth_score"],
    )

    return result
