"""arXiv 论文搜索工具——检索学术论文摘要和链接。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from deep_research_agent.observability.cost_tracker import get_tracker


def search_arxiv_papers(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """返回结构化 arXiv 搜索结果。"""
    try:
        import arxiv

        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = list(client.results(search))
        get_tracker().record_search_call()

        normalized: list[dict[str, Any]] = []
        for i, paper in enumerate(results, 1):
            authors = ", ".join(a.name for a in paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " 等"

            normalized.append(
                {
                    "index": i,
                    "source_type": "arxiv",
                    "title": paper.title,
                    "url": paper.entry_id,
                    "snippet": paper.summary[:300].replace("\n", " "),
                    "authors": authors,
                    "published_at": paper.published.strftime("%Y-%m-%d"),
                }
            )

        logger.info("arXiv 搜索完成: query='{}', 结果数={}", query, len(results))
        return normalized

    except Exception as e:
        logger.error("arXiv 搜索失败: {}", e)
        return []


def format_arxiv_results(results: list[dict[str, Any]]) -> str:
    """格式化 arXiv 搜索结果。"""
    if not results:
        return "arXiv 搜索未返回结果。"

    formatted = []
    for item in results:
        formatted.append(
            f"[{item['index']}] {item['title']}\n"
            f"作者: {item['authors']}\n"
            f"发布时间: {item['published_at']}\n"
            f"链接: {item['url']}\n"
            f"摘要: {item['snippet']}\n"
        )
    return "\n".join(formatted)


@tool
def arxiv_search_tool(query: str, max_results: int = 5) -> str:
    """在 arXiv 上搜索学术论文。

    Args:
        query: 搜索查询语句（建议使用英文）。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的论文列表，含标题、作者、摘要和链接。
    """
    return format_arxiv_results(search_arxiv_papers(query, max_results))
