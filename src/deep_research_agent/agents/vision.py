"""Multimodal vision chat client for image-based research questions (GAIA).

``VisionChat`` mirrors ``LLMChat``: it resolves the vision model credentials
(VISION_MODEL_NAME / VISION_API_KEY / VISION_BASE_URL) from settings, talks to
an OpenAI-compatible ``chat.completions`` endpoint with an ``image_url`` content
part carrying the base64 image, and raises ``LLMChatError`` whenever a call
cannot produce usable content. It keeps the interaction deliberately simple —
a single temperature-0 call per image, with usage recorded on the global cost
tracker.
"""

from __future__ import annotations

import base64
from typing import Any

from openai import AsyncOpenAI

from deep_research_agent.agents.llm import LLMChatError
from deep_research_agent.observability.cost_tracker import get_tracker

_VISION_SYSTEM_PROMPT = (
    "You are an image analysis model. Describe the image factually, transcribe "
    "any visible text verbatim, and never invent content that is not present "
    "in the image."
)


class VisionChat:
    """OpenAI-compatible vision chat client bound to the configured vision model."""

    def __init__(
        self,
        settings: Any | None = None,
        *,
        timeout_seconds: float = 60.0,
    ) -> None:
        from configs.settings import get_settings

        resolved_settings = settings or get_settings()
        self._settings = resolved_settings
        if not resolved_settings.vision_available:
            raise LLMChatError(
                "no vision model credentials configured; set VISION_MODEL_NAME, "
                "VISION_API_KEY, and VISION_BASE_URL in .env"
            )
        self._client = AsyncOpenAI(
            api_key=str(resolved_settings.vision_api_key),
            base_url=str(resolved_settings.vision_base_url),
            timeout=timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return str(self._settings.vision_model_name)

    @staticmethod
    def _build_messages(prompt: str, media_type: str, base64_data: str) -> list[dict[str, Any]]:
        """Build the system + user message pair with the image as a data URL."""
        return [
            {"role": "system", "content": _VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{base64_data}"},
                    },
                ],
            },
        ]

    async def describe_image(
        self,
        *,
        image_bytes: bytes,
        media_type: str,
        prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Describe one image with a single temperature-0 completion.

        Raises ``LLMChatError`` when the call fails or the model returns empty
        content.
        """
        encoded = base64.b64encode(image_bytes).decode("ascii")
        messages = self._build_messages(prompt, media_type, encoded)
        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
            )
        except Exception as exc:  # network and API failures
            raise LLMChatError(f"vision model call failed: {exc}") from exc
        usage = response.usage
        get_tracker().record_llm_call(
            input_tokens=int(usage.prompt_tokens or 0),
            output_tokens=int(usage.completion_tokens or 0),
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise LLMChatError("vision model returned empty content")
        return content

    async def aclose(self) -> None:
        """Release the underlying HTTP client and its connection pool."""
        await self._client.close()
