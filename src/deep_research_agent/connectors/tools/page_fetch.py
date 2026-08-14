"""全文网页抓取工具——把 URL 转成可 grounding 的分块文本。

这个工具补齐了 agent 的"深读"能力：搜索结果只带回 snippet，而事实核对和
引证需要正文。抓取、正文抽取、分块全部是确定性的；SSRF 防护保证工具只能
读取公网 HTTP(S) 资源，不能触碰内网地址。
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

DEFAULT_MAX_CHARS = 12_000
CHUNK_CHARS = 2_000
CHUNK_OVERLAP_CHARS = 200
_HTTP_TIMEOUT_SECONDS = 20.0
_MAX_REDIRECTS = 5
_USER_AGENT = "DeepResearchAgent/1.0 (evidence-first research; contact: repo owner)"

_NOISE_TAGS = {"script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "header", "aside"}


def _is_private_host(hostname: str) -> bool:
    """Return True when the hostname resolves to a private/reserved address."""

    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        return True
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            return True
    return False


def _validate_public_url(url: str) -> str:
    """Validate a URL is public HTTP(S) and its host is not private (SSRF guard)."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"fetch_page only supports http(s) URLs, got scheme {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError("fetch_page requires an absolute URL with a host")
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("fetch_page requires a hostname")
    if _is_private_host(hostname):
        raise ValueError(f"fetch_page refuses non-public host {hostname!r}")
    return url


def _resolve_redirect_target(base: str, location: str) -> str:
    """Resolve a redirect Location header against the current URL."""
    from urllib.parse import urljoin

    return urljoin(base, location)


def _checked_fetch(client: httpx.Client, url: str) -> httpx.Response:
    """Fetch one URL after validating it, and refuse private redirect hops.

    Every hop is validated *before* the request is made: automatic redirect
    following is disabled and each Location is resolved, SSRF-checked, and then
    fetched, so an internal address can never be contacted through a redirect
    (and DNS rebinding is bounded because each hop is resolved and validated
    immediately before connection).
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
        raise ValueError("fetch_page refuses to follow more than 5 redirects")
    return response


def fetch_page(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, object]:
    """Fetch a public web page, extract readable text, and return it as a dict.

    The returned dict is JSON-compatible for the governed tool gateway:
    ``{"url", "final_url", "title", "content", "source_type": "web_page",
    "fetch_status": "ok"}``. ``content`` is whitespace-normalized plain text
    truncated to ``max_chars``.
    """

    _validate_public_url(url)
    try:
        with httpx.Client(
            timeout=_HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = _checked_fetch(client, url)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("fetch_page failed for {}: {}", url, exc)
        raise ValueError(f"fetch_page could not retrieve {url}: {exc}") from exc

    final_url = str(response.url)
    _validate_public_url(final_url)

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        text = response.text[:max_chars]
        title = final_url
        body = text
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        title = (soup.title.string if soup.title and soup.title.string else final_url).strip()[:200]
        body = _normalize_text(main.get_text(" ", strip=False))

    content = _normalize_text(body)[:max_chars]
    return {
        "url": url,
        "final_url": final_url,
        "title": title,
        "content": content,
        "source_type": "web_page",
        "fetch_status": "ok",
    }


def _normalize_text(text: str) -> str:
    """Collapse whitespace while preserving sentence-level boundaries."""

    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, overlap_chars: int = CHUNK_OVERLAP_CHARS) -> list[dict[str, object]]:
    """Deterministic character-window chunking with overlap.

    Returns ``[{"chunk_index", "start", "end", "text"}]``. Every chunk overlaps
    the previous one by ``overlap_chars`` so a claim quoting across a boundary
    still lands inside a single chunk.
    """

    if chunk_chars <= 0 or overlap_chars < 0 or overlap_chars >= chunk_chars:
        raise ValueError("chunk_chars must be positive and overlap_chars must be in [0, chunk_chars)")
    if not text:
        return []
    chunks: list[dict[str, object]] = []
    cursor = 0
    index = 0
    length = len(text)
    while cursor < length:
        end = min(cursor + chunk_chars, length)
        chunks.append({"chunk_index": index, "start": cursor, "end": end, "text": text[cursor:end]})
        index += 1
        if end >= length:
            break
        cursor = max(cursor + chunk_chars - overlap_chars, cursor + 1)
    return chunks
