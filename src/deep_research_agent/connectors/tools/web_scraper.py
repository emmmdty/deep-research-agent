"""网页内容抓取工具——提取指定 URL 的文本内容。"""

from __future__ import annotations

from langchain_core.tools import tool
from loguru import logger

from deep_research_agent.connectors.tools.page_fetch import (
    _MAX_REDIRECTS,
    _resolve_redirect_target,
    _validate_public_url,
)

_SCRAPER_TIMEOUT_SECONDS = 15.0
_MAX_CONTENT_CHARS = 5000


def _checked_scrape(client, url: str) -> str:
    """Fetch one URL after SSRF validation; refuse private redirect hops.

    Every hop is validated *before* the request is made (redirects are followed
    manually), so a redirect into an internal/private address is refused before
    any request reaches it.
    """

    target = _validate_public_url(url)
    response = client.get(target)
    hops = 0
    while response.is_redirect and hops < _MAX_REDIRECTS:
        location = response.headers.get("location")
        if not location:
            break
        next_target = _resolve_redirect_target(target, location)
        _validate_public_url(next_target)
        target = next_target
        response = client.get(target)
        hops += 1
    if hops >= _MAX_REDIRECTS and response.is_redirect:
        raise ValueError("web scraper refuses to follow more than 5 redirects")
    response.raise_for_status()
    return response.text


@tool
def web_scraper_tool(url: str) -> str:
    """抓取指定 URL 的网页内容，提取正文文本。

    Args:
        url: 要抓取的网页 URL。

    Returns:
        提取的网页正文文本（前 5000 字符）。
    """
    import httpx
    from bs4 import BeautifulSoup

    try:
        # 校验通过前不得发起任何请求：拒绝私有地址、非法 scheme。
        _validate_public_url(url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        with httpx.Client(
            timeout=_SCRAPER_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers=headers,
        ) as client:
            html = _checked_scrape(client, url)

        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式标签
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # 清理多余空行
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # 限制长度
        if len(clean_text) > _MAX_CONTENT_CHARS:
            clean_text = clean_text[:_MAX_CONTENT_CHARS] + "\n...(内容已截断)"

        logger.info("网页抓取完成: url='{}', 内容长度={}", url, len(clean_text))
        return clean_text

    except Exception as e:
        logger.error("网页抓取失败: url='{}', 错误={}", url, e)
        # 失败必须作为异常上抛，而不是返回伪装成成功内容的错误字符串：
        # 错误文本被当作页面内容缓存后，会成为"证据"进入 grounding 管线。
        raise ValueError(f"网页抓取失败: {url}: {e}") from e
