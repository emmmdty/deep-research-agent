"""网络搜索工具——支持 Tavily 和 DuckDuckGo 两种后端。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from configs.settings import SearchBackend, get_settings
from evaluation.cost_tracker import get_tracker


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """返回结构化网页搜索结果。"""
    settings = get_settings()
    effective_max_results = max_results or settings.max_search_results

    prefer_tavily = (
        settings.search_backend == SearchBackend.TAVILY and settings.tavily_api_key
    )
    if prefer_tavily:
        results = _search_tavily(query, effective_max_results, settings.tavily_api_key)
        if results:
            return results

    return _search_duckduckgo(query, effective_max_results)


def format_search_results(results: list[dict[str, Any]]) -> str:
    """将结构化搜索结果格式化为字符串。"""
    if not results:
        return "搜索未返回结果。"

    formatted = []
    for item in results:
        formatted.append(
            f"[{item['index']}] {item['title']}\n"
            f"URL: {item['url']}\n"
            f"摘要: {item['snippet']}\n"
        )
    return "\n".join(formatted)


@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """使用搜索引擎搜索信息。优先使用 Tavily，备选 DuckDuckGo。

    Args:
        query: 搜索查询语句。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的搜索结果文本，含标题、URL 和摘要。
    """
    return format_search_results(search_web(query, max_results))


def _search_tavily(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    """通过 Tavily API 执行搜索。"""
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        results = response.get("results", [])
        get_tracker().record_search_call()

        if not results:
            return []

        normalized: list[dict[str, Any]] = []
        for i, r in enumerate(results, 1):
            normalized.append(
                {
                    "index": i,
                    "source_type": "web",
                    "backend": "tavily",
                    "title": r.get("title", "无标题"),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:500],
                }
            )

        logger.info("Tavily 搜索完成: query='{}', 结果数={}", query, len(results))
        return normalized

    except Exception as e:
        logger.warning("Tavily 搜索失败: {}，回退到 DuckDuckGo", e)
        return []


def _search_duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    """通过 DuckDuckGo 执行搜索（无需 API key）。"""
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(item)
        get_tracker().record_search_call()

        if not results:
            return []

        normalized: list[dict[str, Any]] = []
        for i, r in enumerate(results, 1):
            normalized.append(
                {
                    "index": i,
                    "source_type": "web",
                    "backend": "duckduckgo",
                    "title": r.get("title", "无标题"),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:500],
                }
            )

        logger.info("DuckDuckGo 搜索完成: query='{}', 结果数={}", query, len(results))
        return normalized

    except Exception as e:
        logger.error("DuckDuckGo 搜索失败: {}", e)
        return []
