"""GitHub 搜索工具——搜索 GitHub 仓库和代码。"""

from __future__ import annotations

from langchain_core.tools import tool
from loguru import logger


@tool
def github_search_tool(query: str, max_results: int = 5) -> str:
    """在 GitHub 上搜索相关仓库。

    Args:
        query: 搜索查询语句。
        max_results: 返回的最大结果数量，默认 5。

    Returns:
        格式化的仓库列表，含名称、描述、Stars 数和链接。
    """
    try:
        import httpx

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DeepResearchAgent/1.0",
        }

        response = httpx.get(
            "https://api.github.com/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results,
            },
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if not items:
            return "GitHub 搜索未返回结果。"

        formatted = []
        for i, repo in enumerate(items, 1):
            name = repo.get("full_name", "")
            desc = repo.get("description", "无描述") or "无描述"
            stars = repo.get("stargazers_count", 0)
            url = repo.get("html_url", "")
            language = repo.get("language", "未知")
            updated = repo.get("updated_at", "")[:10]

            formatted.append(
                f"[{i}] {name} ⭐ {stars}\n"
                f"语言: {language} | 更新: {updated}\n"
                f"描述: {desc[:200]}\n"
                f"链接: {url}\n"
            )

        logger.info("GitHub 搜索完成: query='{}', 结果数={}", query, len(items))
        return "\n".join(formatted)

    except Exception as e:
        logger.error("GitHub 搜索失败: {}", e)
        return f"GitHub 搜索失败: {e}"
