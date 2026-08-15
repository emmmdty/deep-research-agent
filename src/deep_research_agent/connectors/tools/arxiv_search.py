"""arXiv 论文搜索工具——检索学术论文摘要和链接。

一手来源策略：每条结果附带 arXiv 官方 HTML 全文链接（fulltext_url），
优先引导 agent 读取 arXiv 生成的可解析全文而非第三方镜像。
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import tool
from loguru import logger

from deep_research_agent.observability.cost_tracker import get_tracker

# arXiv 论文 id：新式 "2401.12345[vN]"，或旧式 "cond-mat/0309395[vN]"。
_ARXIV_ID_RE = re.compile(
    r"^(?:(?:[0-9]{4}\.[0-9]{4,5})|(?:[a-z][a-z0-9\-]*(?:\.[A-Z]{2})?/[0-9]{7}))(?:v[0-9]+)?$"
)
_ARXIV_URL_RE = re.compile(
    r"^(?:https?://)?arxiv\.org/(?P<kind>abs|pdf|html)/(?P<id>[^?#\s]+?)(?:\.pdf)?$"
)


def arxiv_fulltext_url(entry_id: str) -> str:
    """把 arXiv 引用形式映射为官方 HTML 全文 URL。

    ``https://arxiv.org/abs/2401.12345v2``、``http://arxiv.org/abs/2401.12345``、
    ``https://arxiv.org/pdf/2401.12345v2.pdf``、裸 id ``2401.12345v2`` 以及
    已经是 html 的 URL 都归一化为 ``https://arxiv.org/html/<id>``（保留版本
    后缀；scheme 归一为 https）。不是 arXiv 引用的输入——包括带
    ``arXiv:`` 前缀的形式和任意垃圾串——返回 ""。
    """

    value = entry_id.strip()
    if not value or value.lower().startswith("arxiv:"):
        return ""
    match = _ARXIV_URL_RE.match(value)
    if match:
        kind, raw_id = match.group("kind"), match.group("id")
        if kind == "html" or _ARXIV_ID_RE.match(raw_id):
            return f"https://arxiv.org/html/{raw_id}"
        return ""
    if _ARXIV_ID_RE.match(value):
        return f"https://arxiv.org/html/{value}"
    return ""


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
                    "fulltext_url": arxiv_fulltext_url(paper.entry_id),
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
        lines = [
            f"[{item['index']}] {item['title']}\n",
            f"作者: {item['authors']}\n",
            f"发布时间: {item['published_at']}\n",
            f"链接: {item['url']}\n",
        ]
        fulltext_url = item.get("fulltext_url", "")
        if fulltext_url:
            lines.append(f"全文: {fulltext_url}\n")
        lines.append(f"摘要: {item['snippet']}\n")
        formatted.append("".join(lines))
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
