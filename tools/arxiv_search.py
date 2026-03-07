"""arXiv 论文搜索工具——检索学术论文摘要和链接。"""

from __future__ import annotations

from langchain_core.tools import tool
from loguru import logger


@tool
def arxiv_search_tool(query: str, max_results: int = 5) -> str:
    """在 arXiv 上搜索学术论文。

    Args:
        query: 搜索查询语句（建议使用英文）。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的论文列表，含标题、作者、摘要和链接。
    """
    try:
        import arxiv

        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = list(client.results(search))

        if not results:
            return "arXiv 搜索未返回结果。"

        formatted = []
        for i, paper in enumerate(results, 1):
            authors = ", ".join(a.name for a in paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " 等"

            summary = paper.summary[:300].replace("\n", " ")
            formatted.append(
                f"[{i}] {paper.title}\n"
                f"作者: {authors}\n"
                f"发布时间: {paper.published.strftime('%Y-%m-%d')}\n"
                f"链接: {paper.entry_id}\n"
                f"摘要: {summary}\n"
            )

        logger.info("arXiv 搜索完成: query='{}', 结果数={}", query, len(results))
        return "\n".join(formatted)

    except Exception as e:
        logger.error("arXiv 搜索失败: {}", e)
        return f"arXiv 搜索失败: {e}"
