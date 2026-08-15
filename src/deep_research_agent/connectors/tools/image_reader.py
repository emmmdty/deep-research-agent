"""图像读取工具——把图片 URL 转成可 grounding 的描述/OCR 文本。

``read_image`` 补全多模态入口（GAIA 图像类问题）：搜索工具只能发现文本，
而答案可能藏在图片里。工具校验公网 URL（复用 ``page_fetch`` 的 SSRF 防护）、
下载图片、用 ``VisionChat`` 做事实性描述 + 逐字转写，任何失败都转成
``ValueError``，与 ``fetch_page`` 的网关处理风格保持一致。
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx
from loguru import logger

from deep_research_agent.agents.llm import LLMChatError
from deep_research_agent.agents.vision import VisionChat
from deep_research_agent.connectors.tools.page_fetch import (
    _USER_AGENT,
    _checked_fetch,
    _validate_public_url,
)

_DEFAULT_IMAGE_PROMPT = "Describe this image factually and transcribe any visible text verbatim."
_HTTP_TIMEOUT_SECONDS = 45.0
_MAX_BYTES = 5_000_000


def read_image(
    image_url: str,
    prompt: str | None = None,
    *,
    max_bytes: int = _MAX_BYTES,
) -> dict[str, Any]:
    """Fetch an image from a public URL and describe it with the vision model.

    Returns ``{"url", "final_url", "media_type", "content", "source_type":
    "image_ocr", "fetch_status": "ok", "vision_model"}``. Raises ``ValueError``
    when vision is not configured, the URL is private, the fetch fails, the
    content is not an image, or the model call fails.
    """

    _validate_public_url(image_url)
    try:
        chat = VisionChat()
    except LLMChatError as exc:
        raise ValueError(f"read_image unavailable: {exc}") from exc
    try:
        with httpx.Client(
            timeout=_HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = _checked_fetch(client, image_url)
        response.raise_for_status()
        final_url = str(response.url)
        # Every redirect hop was validated before its request inside
        # ``_checked_fetch``; this final check is defense-in-depth.
        _validate_public_url(final_url)
        media_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not media_type.startswith("image/"):
            raise ValueError(
                f"read_image expected image content, got content-type {media_type!r} from {final_url}"
            )
        content = response.content
        if len(content) > max_bytes:
            raise ValueError(
                f"read_image refuses image larger than {max_bytes} bytes "
                f"({len(content)} bytes from {final_url})"
            )
        described = asyncio.run(
            chat.describe_image(
                image_bytes=content,
                media_type=media_type,
                prompt=prompt or _DEFAULT_IMAGE_PROMPT,
            )
        )
    except LLMChatError as exc:
        raise ValueError(f"read_image model call failed: {exc}") from exc
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - gateway handlers surface all failures as ValueError
        logger.warning("read_image failed for {}: {}", image_url, exc)
        raise ValueError(f"read_image could not retrieve {image_url}: {exc}") from exc
    finally:
        with contextlib.suppress(Exception):
            asyncio.run(chat.aclose())
    return {
        "url": image_url,
        "final_url": final_url,
        "media_type": media_type,
        "content": described,
        "source_type": "image_ocr",
        "fetch_status": "ok",
        "vision_model": chat.model_name,
    }
