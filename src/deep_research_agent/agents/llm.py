"""Minimal OpenAI-compatible chat client with JSON extraction and token accounting."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from deep_research_agent.observability.cost_tracker import get_tracker


class LLMChatError(RuntimeError):
    """Raised when a model call cannot produce a usable response."""


def _is_rate_limit(exc: Exception) -> bool:
    """Detect provider quota/rate-limit errors that retrying cannot fix."""

    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    message = str(exc)
    return "429" in message or "rate limit" in message.lower() or "usage limit" in message.lower()


def extract_json(text: str) -> Any:
    """Extract the first JSON value from a model response, tolerating fences and prose."""

    if not text or not text.strip():
        raise LLMChatError("model returned an empty response")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    if start < 0:
        raise LLMChatError("model response contains no JSON object")
    try:
        return json.loads(candidate[start:])
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", candidate):
        try:
            value, _ = decoder.raw_decode(candidate[match.start() :])
            return value
        except json.JSONDecodeError:
            continue
    balanced = _extract_balanced_json(candidate)
    if balanced is None:
        raise LLMChatError("model response is not valid JSON")
    return balanced


def _extract_balanced_json(text: str) -> Any:
    """Locate the outermost balanced JSON object as a last-resort extraction."""

    stack: list[int] = []
    for index, char in enumerate(text):
        if char == "{":
            stack.append(index)
        elif char == "}" and stack:
            start = stack.pop()
            if not stack:
                try:
                    return json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


class LLMChat:
    """OpenAI-compatible chat helper bound to the configured default provider."""

    def __init__(
        self,
        settings: Any | None = None,
        *,
        timeout_seconds: float = 180.0,
    ) -> None:
        from configs.settings import get_settings

        resolved_settings = settings or get_settings()
        self._model = resolved_settings.get_llm_config()
        if not self._model.get("api_key"):
            raise LLMChatError(
                "no LLM credentials configured; set LLM_API_KEY / LLM_BASE_URL in .env"
            )
        self._client = AsyncOpenAI(
            api_key=str(self._model["api_key"]),
            base_url=str(self._model["base_url"] or None),
            timeout=timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return str(self._model["model"])

    async def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Run one chat completion and record usage on the global tracker."""

        kwargs: dict[str, Any] = {
            "model": self._model["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._model["temperature"] if temperature is None else temperature,
            "max_tokens": max_tokens or int(self._model.get("max_tokens") or 4096),
        }
        last_error: Exception | None = None
        budget_attempts = 0
        for attempt in range(1, 4):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                usage = response.usage
                get_tracker().record_llm_call(
                    input_tokens=int(usage.prompt_tokens or 0),
                    output_tokens=int(usage.completion_tokens or 0),
                )
                content = response.choices[0].message.content or ""
                if not content.strip():
                    details = usage.completion_tokens_details
                    reasoning = details.reasoning_tokens if details else 0
                    if reasoning and int(reasoning or 0) >= int(kwargs["max_tokens"]):
                        # Thinking models sometimes consume the entire token
                        # budget on reasoning; widen the budget and retry.
                        if budget_attempts < 2:
                            kwargs["max_tokens"] = min(int(kwargs["max_tokens"]) * 2, 16384)
                            budget_attempts += 1
                            logger.warning(
                                "LLM reasoning consumed the token budget; widening to {} and retrying",
                                kwargs["max_tokens"],
                            )
                            continue
                    raise LLMChatError(
                        f"model returned empty content (prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"reasoning_tokens={reasoning})"
                    )
                return content
            except Exception as exc:  # network and API retryable failures
                if _is_rate_limit(exc):
                    raise LLMChatError(f"LLM rate limit reached: {exc}") from exc
                last_error = exc
                logger.warning("LLM call attempt {} failed: {}", attempt, exc)
        raise LLMChatError(f"LLM call failed after 3 attempts: {last_error}")

    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Run a chat completion and parse the response as a JSON object.

        If the first parse fails, one corrective turn ("output JSON only") is
        sent so common fence/prose formatting drift does not sink the call.
        """

        content = await self.chat(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            value = extract_json(content)
        except LLMChatError:
            corrected = await self.chat(
                system=system,
                user=user + "\n\nIMPORTANT: reply with a single valid JSON object only.",
                max_tokens=max_tokens,
                temperature=temperature,
            )
            value = extract_json(corrected)
            logger.info("recovered non-JSON model response after corrective turn")
        if not isinstance(value, dict):
            raise LLMChatError("model JSON response is not an object")
        return value
