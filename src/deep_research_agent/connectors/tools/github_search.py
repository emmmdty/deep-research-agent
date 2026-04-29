"""GitHub 搜索工具——搜索 GitHub 仓库和代码。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from deep_research_agent.observability.cost_tracker import get_tracker


def search_github_repositories(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """返回结构化 GitHub 仓库搜索结果。"""
    import httpx

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DeepResearchAgent/1.0",
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(http2=False, timeout=15, follow_redirects=True) as client:
                response = client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": max_results,
                    },
                    headers=headers,
                )
            response.raise_for_status()
            get_tracker().record_search_call()

            data = response.json()
            items = data.get("items", [])
            normalized: list[dict[str, Any]] = []
            for i, repo in enumerate(items, 1):
                normalized.append(
                    {
                        "index": i,
                        "source_type": "github",
                        "title": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "snippet": (repo.get("description", "无描述") or "无描述")[:200],
                        "owner": (repo.get("owner") or {}).get("login", ""),
                        "owner_type": (repo.get("owner") or {}).get("type", ""),
                        "topics": repo.get("topics", []) or [],
                        "homepage": repo.get("homepage", "") or "",
                        "archived": bool(repo.get("archived", False)),
                        "fork": bool(repo.get("fork", False)),
                        "default_branch": repo.get("default_branch", "") or "",
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language", "未知"),
                        "updated_at": repo.get("updated_at", "")[:10],
                    }
                )

            logger.info("GitHub 搜索完成: query='{}', 结果数={}", query, len(items))
            return normalized
        except Exception as exc:
            last_error = exc
            logger.warning("GitHub 搜索第 {} 次失败: {}", attempt, exc)

    logger.error("GitHub 搜索失败: {}", last_error)
    return []


def format_github_results(results: list[dict[str, Any]]) -> str:
    """格式化 GitHub 仓库结果。"""
    if not results:
        return "GitHub 搜索未返回结果。"

    formatted = []
    for item in results:
        formatted.append(
            f"[{item['index']}] {item['title']} ⭐ {item['stars']}\n"
            f"语言: {item['language']} | 更新: {item['updated_at']}\n"
            f"描述: {item['snippet']}\n"
            f"链接: {item['url']}\n"
        )
    return "\n".join(formatted)


@tool
def github_search_tool(query: str, max_results: int = 5) -> str:
    """在 GitHub 上搜索相关仓库。

    Args:
        query: 搜索查询语句。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的仓库列表，含名称、描述、Stars 数和链接。
    """
    return format_github_results(search_github_repositories(query, max_results))
