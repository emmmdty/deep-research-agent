"""Minimal OpenAI-compatible chat client with JSON extraction and token accounting.

The client exposes two interaction styles:

- ``chat`` / ``chat_json`` — plain completions with prompt-based JSON extraction
  (works on every provider, including those without a JSON mode).
- ``chat_with_tools`` / ``tool_loop`` — native function calling via the
  ``tools`` API. ``tool_loop`` owns the multi-turn loop: the model proposes
  tool calls, the caller executes them, results are fed back as ``tool``
  messages, and the loop repeats until the model answers or the round cap is
  hit. Parallel tool calls from one assistant turn are supported.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from loguru import logger

from openai import AsyncOpenAI

from deep_research_agent.observability.cost_tracker import get_tracker

class LLMChatError(RuntimeError):
    """Raised when a model call cannot produce a usable response."""


# Retries with exponential backoff + jitter: a 429 is precisely what backoff
# fixes, so rate limits are retried (honoring Retry-After when present) before
# being surfaced as errors.
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 1.0
_BACKOFF_CAP_SECONDS = 8.0
_RATE_LIMIT_BACKOFF_SECONDS = 2.0


def _is_rate_limit(exc: Exception) -> bool:
    """Detect provider quota/rate-limit errors that warrant a backed-off retry."""

    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    message = str(exc)
    return "429" in message or "rate limit" in message.lower() or "usage limit" in message.lower()


def _retry_after_seconds(exc: Exception) -> float | None:
    """Best-effort Retry-After header extraction for provider rate limits."""

    for attr in ("headers", "response"):
        raw = getattr(exc, attr, None)
        headers = getattr(raw, "headers", None)
        if headers is None and isinstance(raw, dict):
            headers = raw
        if not headers:
            continue
        try:
            value = headers.get("retry-after") or headers.get("Retry-After")
        except Exception:  # noqa: BLE001 - malformed headers must not break retries
            continue
        if not value:
            continue
        try:
            return max(float(value), 0.0)
        except (TypeError, ValueError):
            continue
    return None


async def _backoff_delay(attempt: int, *, rate_limited: bool = False) -> None:
    """Sleep with exponential backoff and jitter before a retry."""

    if rate_limited:
        delay = _RATE_LIMIT_BACKOFF_SECONDS * (2 ** (attempt - 1))
    else:
        delay = min(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), _BACKOFF_CAP_SECONDS)
    await asyncio.sleep(delay * (0.5 + random.random()))


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


@dataclass(frozen=True)
class ToolCallRecord:
    """One tool call the model proposed, with its parsed arguments."""

    call_id: str
    name: str
    arguments: dict[str, Any]
    round: int


@dataclass
class ToolLoopResult:
    """Transcript of a multi-turn function-calling loop."""

    content: str | None = None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    rounds: int = 0

    @property
    def tool_names(self) -> list[str]:
        return [call.name for call in self.tool_calls]

    def calls_of(self, name: str) -> list[ToolCallRecord]:
        return [call for call in self.tool_calls if call.name == name]

    def first_arguments(self, name: str) -> dict[str, Any] | None:
        for call in self.tool_calls:
            if call.name == name:
                return call.arguments
        return None


@runtime_checkable
class ToolLoopChat(Protocol):
    """Capability marker: a chat client that supports native function calling.

    Deterministic fakes and provider adapters without tool support simply omit
    ``tool_loop``; agent roles check this protocol and degrade gracefully.
    """

    @property
    def model_name(self) -> str: ...

    async def tool_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        execute_tool: Any,
        max_rounds: int = 3,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ToolLoopResult: ...


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
    return {}


def _canonical_tool_definitions(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return tool definitions in the provider wire format (dict)."""

    canonical: list[dict[str, Any]] = []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("type") == "function":
            canonical.append(tool)
        elif isinstance(tool, dict) and "function" in tool:
            canonical.append(tool)
        elif isinstance(tool, dict):
            canonical.append(
                {"type": "function", "function": {"name": tool["name"], "parameters": tool.get("parameters", {})}}
            )
    return canonical


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
        # Thinking models (e.g. DeepSeek reasoning variants) can burn the whole
        # output budget on reasoning and return empty content; the endpoint lets
        # us disable thinking explicitly for deterministic agent steps.
        self._thinking_disabled = bool(
            getattr(resolved_settings, "llm_disable_thinking", False)
        )

    @property
    def model_name(self) -> str:
        return str(self._model["model"])

    async def aclose(self) -> None:
        """Release the underlying HTTP client and its connection pool."""
        await self._client.close()

    def _request_kwargs(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._model["model"],
            "messages": messages,
            "temperature": self._model["temperature"] if temperature is None else temperature,
            "max_tokens": max_tokens or int(self._model.get("max_tokens") or 4096),
        }
        if self._thinking_disabled:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        return kwargs

    async def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Run one chat completion and record usage on the global tracker."""

        kwargs = self._request_kwargs(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        last_error: Exception | None = None
        budget_attempts = 0
        for attempt in range(1, _MAX_ATTEMPTS + 1):
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
                    budget = int(kwargs["max_tokens"])
                    if reasoning and int(reasoning or 0) >= budget * 0.9:
                        # Thinking models often consume nearly the entire token
                        # budget on reasoning; widen the budget and retry.
                        if budget_attempts < 2:
                            kwargs["max_tokens"] = min(budget * 2, 16384)
                            budget_attempts += 1
                            logger.warning(
                                "LLM reasoning consumed the token budget; widening to {} and retrying",
                                kwargs["max_tokens"],
                            )
                            continue
                        # The model's reasoning can grow to fill any budget. Reset
                        # the budget and ask for a direct answer without reasoning.
                        kwargs["max_tokens"] = max_tokens or int(self._model.get("max_tokens") or 4096)
                        kwargs["messages"] = [
                            {"role": "system", "content": system},
                            {
                                "role": "user",
                                "content": user
                                + "\n\nIMPORTANT: Answer immediately with the final "
                                "content only. Do not think step by step or reason aloud.",
                            },
                        ]
                        logger.warning(
                            "LLM reasoning overflowed the widened budget; retrying with a direct-answer instruction"
                        )
                        continue
                    raise LLMChatError(
                        f"model returned empty content (prompt_tokens={usage.prompt_tokens}, "
                        f"completion_tokens={usage.completion_tokens}, "
                        f"reasoning_tokens={reasoning})"
                    )
                return content
            except Exception as exc:  # network and API retryable failures
                if _is_rate_limit(exc) and attempt < _MAX_ATTEMPTS:
                    retry_after = _retry_after_seconds(exc)
                    delay = retry_after if retry_after is not None else _BACKOFF_BASE_SECONDS
                    logger.warning(
                        "LLM rate limit on attempt {}; retrying in {:.1f}s", attempt, delay
                    )
                    await asyncio.sleep(delay * (0.5 + random.random()))
                    last_error = exc
                    continue
                if attempt >= _MAX_ATTEMPTS:
                    raise LLMChatError(f"LLM call failed after {_MAX_ATTEMPTS} attempts: {exc}") from exc
                last_error = exc
                await _backoff_delay(attempt, rate_limited=_is_rate_limit(exc))
                logger.warning("LLM call attempt {} failed: {}", attempt, exc)
        raise LLMChatError(f"LLM call failed after {_MAX_ATTEMPTS} attempts: {last_error}")

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

    async def chat_with_tools(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        tool_choice: Any = "auto",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """One completion with the provider's native ``tools`` API.

        Returns ``{"content": str | None, "tool_calls": [ToolCallRecord, ...]}``.
        Raises ``LLMChatError`` on unrecoverable provider failures so callers
        can fall back to prompt-based JSON extraction.
        """

        kwargs = self._request_kwargs(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        kwargs["tools"] = _canonical_tool_definitions(tools)
        kwargs["tool_choice"] = tool_choice
        last_error: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                usage = response.usage
                get_tracker().record_llm_call(
                    input_tokens=int(usage.prompt_tokens or 0),
                    output_tokens=int(usage.completion_tokens or 0),
                )
                message = response.choices[0].message
                tool_calls = [
                    ToolCallRecord(
                        call_id=str(call.id or f"call-{index}"),
                        name=str(call.function.name or ""),
                        arguments=_parse_tool_arguments(call.function.arguments),
                        round=0,
                    )
                    for index, call in enumerate(message.tool_calls or [])
                ]
                return {
                    "content": message.content or None,
                    "tool_calls": tool_calls,
                }
            except Exception as exc:  # network and API retryable failures
                if _is_rate_limit(exc) and attempt < _MAX_ATTEMPTS:
                    retry_after = _retry_after_seconds(exc)
                    delay = retry_after if retry_after is not None else _BACKOFF_BASE_SECONDS
                    logger.warning(
                        "LLM tool call rate limit on attempt {}; retrying in {:.1f}s",
                        attempt,
                        delay,
                    )
                    await asyncio.sleep(delay * (0.5 + random.random()))
                    last_error = exc
                    continue
                if attempt >= _MAX_ATTEMPTS:
                    raise LLMChatError(
                        f"LLM tool call failed after {_MAX_ATTEMPTS} attempts: {exc}"
                    ) from exc
                last_error = exc
                await _backoff_delay(attempt, rate_limited=_is_rate_limit(exc))
                logger.warning("LLM tool call attempt {} failed: {}", attempt, exc)
        raise LLMChatError(f"LLM tool call failed after {_MAX_ATTEMPTS} attempts: {last_error}")

    async def tool_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        execute_tool: Any,
        max_rounds: int = 3,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ToolLoopResult:
        """Own the multi-turn tool loop: propose calls, execute, feed back.

        Each assistant turn may contain several parallel tool calls; every call
        is executed and its JSON result is appended as a ``tool`` message before
        the next completion. The loop ends when the model answers with plain
        content, when no tool calls are proposed, or when ``max_rounds`` is hit.
        """

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        recorded: list[ToolCallRecord] = []
        canonical_tools = _canonical_tool_definitions(tools)
        for round_index in range(1, max_rounds + 1):
            request_kwargs = self._request_kwargs(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            request_kwargs["tools"] = canonical_tools
            request_kwargs["tool_choice"] = "auto"
            try:
                response = await self._client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                if _is_rate_limit(exc) and round_index < max_rounds:
                    retry_after = _retry_after_seconds(exc)
                    delay = retry_after if retry_after is not None else _BACKOFF_BASE_SECONDS
                    logger.warning(
                        "LLM tool loop rate limit at round {}; retrying in {:.1f}s",
                        round_index,
                        delay,
                    )
                    await asyncio.sleep(delay * (0.5 + random.random()))
                    continue
                if round_index < max_rounds:
                    await _backoff_delay(round_index, rate_limited=_is_rate_limit(exc))
                    logger.warning("LLM tool loop round {} failed: {}", round_index, exc)
                    continue
                raise LLMChatError(
                    f"LLM tool loop failed after {max_rounds} attempts: {exc}"
                ) from exc
            usage = response.usage
            get_tracker().record_llm_call(
                input_tokens=int(usage.prompt_tokens or 0),
                output_tokens=int(usage.completion_tokens or 0),
            )
            message = response.choices[0].message
            proposed = [
                ToolCallRecord(
                    call_id=str(call.id or f"call-{round_index}-{index}"),
                    name=str(call.function.name or ""),
                    arguments=_parse_tool_arguments(call.function.arguments),
                    round=round_index,
                )
                for index, call in enumerate(message.tool_calls or [])
            ]
            if not proposed:
                return ToolLoopResult(content=message.content or None, tool_calls=recorded, rounds=round_index)
            recorded.extend(proposed)
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": call.call_id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)},
                        }
                        for call in proposed
                    ],
                }
            )
            for call in proposed:
                try:
                    result = await execute_tool(call.name, call.arguments)
                except Exception as exc:
                    result = {"error": str(exc) or type(exc).__name__}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
        return ToolLoopResult(content=None, tool_calls=recorded, rounds=max_rounds)
