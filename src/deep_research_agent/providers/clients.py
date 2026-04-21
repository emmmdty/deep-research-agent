"""Concrete chat-model factories behind the provider router."""

from __future__ import annotations

from typing import Optional

from langchain_openai import ChatOpenAI

from configs.settings import Settings, get_settings
from evaluation.cost_tracker import get_tracker
from deep_research_agent.providers.models import ProviderProfile, ProviderRouteRequest, ProviderType
from deep_research_agent.providers.router import ProviderRouter

try:  # pragma: no cover - exercised only when Anthropic models are materialized
    from langchain_anthropic import ChatAnthropic as _BaseChatAnthropic
except ImportError:  # pragma: no cover - explicit runtime error on use
    class _BaseChatAnthropic:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            raise ImportError("langchain-anthropic is required for Anthropic provider profiles")


def _estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(len(text) // 4, 1)


def _extract_token_usage(response) -> tuple[int, int]:
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = metadata.get("token_usage") or metadata.get("usage") or {}
    input_tokens = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("prompt_token_count")
        or getattr(getattr(response, "usage_metadata", {}), "get", lambda *_: 0)("input_tokens")
        or 0
    )
    output_tokens = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("candidates_token_count")
        or getattr(getattr(response, "usage_metadata", {}), "get", lambda *_: 0)("output_tokens")
        or 0
    )
    if input_tokens or output_tokens:
        return input_tokens, output_tokens
    content = getattr(response, "content", "")
    return 0, _estimate_tokens_from_text(str(content))


def _response_text(response) -> str:
    text_attr = getattr(response, "text", None)
    if callable(text_attr):
        return str(text_attr())
    if text_attr is not None:
        return str(text_attr)
    return str(getattr(response, "content", ""))


class TrackedChatOpenAI(ChatOpenAI):
    """ChatOpenAI with usage tracking."""

    def invoke(self, input, config=None, **kwargs):
        response = super().invoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(input_tokens=input_tokens, output_tokens=output_tokens)
        return response

    async def ainvoke(self, input, config=None, **kwargs):
        response = await super().ainvoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(input_tokens=input_tokens, output_tokens=output_tokens)
        return response


class TrackedChatAnthropic(_BaseChatAnthropic):
    """ChatAnthropic with usage tracking."""

    def invoke(self, input, config=None, **kwargs):
        response = super().invoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(input_tokens=input_tokens, output_tokens=output_tokens)
        return response

    async def ainvoke(self, input, config=None, **kwargs):
        response = await super().ainvoke(input, config=config, **kwargs)
        input_tokens, output_tokens = _extract_token_usage(response)
        get_tracker().record_llm_call(input_tokens=input_tokens, output_tokens=output_tokens)
        return response


def build_chat_model(profile: ProviderProfile):
    if profile.provider_type in {ProviderType.OPENAI, ProviderType.OPENAI_COMPATIBLE}:
        return TrackedChatOpenAI(
            model=profile.model,
            api_key=profile.api_key,
            base_url=profile.base_url,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
        )
    return TrackedChatAnthropic(
        model=profile.model,
        api_key=profile.api_key,
        base_url=profile.base_url,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
    )


class LLMProvider:
    """Compatibility wrapper over the canonical provider router."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        task_role: str = "planning",
        provider_profile: str | None = None,
        routing_mode: str = "auto",
    ) -> None:
        self._settings = settings or get_settings()
        self._task_role = task_role
        self._provider_profile = provider_profile
        self._routing_mode = routing_mode
        self._selection = None
        self._llm = None

    @property
    def selection(self):
        if self._selection is None:
            router = ProviderRouter(self._settings)
            self._selection = router.route(
                ProviderRouteRequest(
                    task_role=self._task_role,
                    provider_profile=self._provider_profile,
                    routing_mode=self._routing_mode,
                    current_provider=self._settings.get_default_provider_profile_name(),
                )
            )
        return self._selection

    @property
    def llm(self):
        if self._llm is None:
            self._llm = build_chat_model(self.selection.profile)
        return self._llm

    def chat(self, messages: list[dict]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        response = self.llm.invoke(lc_messages)
        return _response_text(response)

    async def achat(self, messages: list[dict]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        response = await self.llm.ainvoke(lc_messages)
        return _response_text(response)


def get_llm(
    settings: Optional[Settings] = None,
    *,
    task_role: str = "planning",
    provider_profile: str | None = None,
    routing_mode: str = "auto",
):
    provider = LLMProvider(
        settings,
        task_role=task_role,
        provider_profile=provider_profile,
        routing_mode=routing_mode,
    )
    return provider.llm
