"""OpenAI-compatible client materialization behind a narrow factory."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

from deep_research_agent.model_runtime.models import ResolvedModelEndpoint
from deep_research_agent.model_runtime.registry import ModelRegistry


ModelBuilder = Callable[..., object]


@dataclass(frozen=True)
class OpenAICompatibleClient:
    """Materialized client plus non-secret endpoint capabilities."""

    endpoint_id: str
    model_name: str
    supports_structured_output: bool
    supports_tool_use: bool
    runtime_model: object = field(repr=False, compare=False)


def _build_pydantic_ai_model(
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout_seconds: float,
    supports_structured_output: bool,
    supports_tool_use: bool,
) -> OpenAIChatModel:
    openai_client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
    )
    provider = OpenAIProvider(openai_client=openai_client)
    profile = OpenAIModelProfile(
        supports_tools=supports_tool_use,
        supports_json_schema_output=supports_structured_output,
        supports_json_object_output=supports_structured_output,
    )
    return OpenAIChatModel(model, provider=provider, profile=profile)


class OpenAICompatibleClientFactory:
    """Builds one independent client from each audited resolution."""

    def __init__(
        self,
        *,
        registry: ModelRegistry,
        model_builder: ModelBuilder | None = None,
    ) -> None:
        self._registry = registry
        self._model_builder = model_builder or _build_pydantic_ai_model

    def create(self, resolved: ResolvedModelEndpoint) -> OpenAICompatibleClient:
        runtime_model = self._model_builder(
            base_url=str(resolved.base_url),
            model=resolved.model,
            api_key=self._registry._api_key_for_client(resolved.credential_id),
            timeout_seconds=resolved.timeout_seconds,
            supports_structured_output=resolved.supports_structured_output,
            supports_tool_use=resolved.supports_tool_use,
        )
        return OpenAICompatibleClient(
            endpoint_id=resolved.endpoint_id,
            model_name=resolved.model,
            supports_structured_output=resolved.supports_structured_output,
            supports_tool_use=resolved.supports_tool_use,
            runtime_model=runtime_model,
        )
