"""网页内容抓取工具——提取指定 URL 的文本内容。"""

from __future__ import annotations

from langchain_core.tools import tool
from loguru import logger


@tool
def web_scraper_tool(url: str) -> str:
    """抓取指定 URL 的网页内容，提取正文文本。

    Args:
        url: 要抓取的网页 URL。

    Returns:
        提取的网页正文文本（前 5000 字符）。
    """
    try:
        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 移除脚本和样式标签
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # 清理多余空行
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # 限制长度
        if len(clean_text) > 5000:
            clean_text = clean_text[:5000] + "\n...(内容已截断)"

        logger.info("网页抓取完成: url='{}', 内容长度={}", url, len(clean_text))
        return clean_text

    except Exception as e:
        logger.error("网页抓取失败: url='{}', 错误={}", url, e)
        return f"网页抓取失败: {e}"
