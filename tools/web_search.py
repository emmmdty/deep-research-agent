"""网络搜索工具——支持 Tavily 和 DuckDuckGo 两种后端。"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool
from loguru import logger


@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """使用搜索引擎搜索信息。优先使用 Tavily，备选 DuckDuckGo。

    Args:
        query: 搜索查询语句。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的搜索结果文本，含标题、URL 和摘要。
    """
    from configs.settings import get_settings

    settings = get_settings()

    # 优先使用 Tavily
    if settings.tavily_api_key:
        return _search_tavily(query, max_results, settings.tavily_api_key)

    # 备选 DuckDuckGo
    return _search_duckduckgo(query, max_results)


def _search_tavily(query: str, max_results: int, api_key: str) -> str:
    """通过 Tavily API 执行搜索。"""
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        results = response.get("results", [])

        if not results:
            return "搜索未返回结果。"

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            url = r.get("url", "")
            content = r.get("content", "")[:500]
            formatted.append(f"[{i}] {title}\nURL: {url}\n摘要: {content}\n")

        logger.info("Tavily 搜索完成: query='{}', 结果数={}", query, len(results))
        return "\n".join(formatted)

    except Exception as e:
        logger.warning("Tavily 搜索失败: {}，回退到 DuckDuckGo", e)
        return _search_duckduckgo(query, max_results)


def _search_duckduckgo(query: str, max_results: int) -> str:
    """通过 DuckDuckGo 执行搜索（无需 API key）。"""
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(item)

        if not results:
            return "搜索未返回结果。"

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            url = r.get("href", "")
            body = r.get("body", "")[:500]
            formatted.append(f"[{i}] {title}\nURL: {url}\n摘要: {body}\n")

        logger.info("DuckDuckGo 搜索完成: query='{}', 结果数={}", query, len(results))
        return "\n".join(formatted)

    except Exception as e:
        logger.error("DuckDuckGo 搜索失败: {}", e)
        return f"搜索失败: {e}"
