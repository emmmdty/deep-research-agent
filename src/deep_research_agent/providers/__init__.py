"""Canonical provider boundary exposed from the src package."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "LLMProvider",
    "ProviderCapabilities",
    "ProviderProfile",
    "ProviderRouteRequest",
    "ProviderRouter",
    "ProviderSelection",
    "ProviderType",
    "RoutingMode",
    "TrackedChatAnthropic",
    "TrackedChatOpenAI",
    "get_llm",
]


def __getattr__(name: str):
    if name in {"ProviderCapabilities", "ProviderProfile", "ProviderRouteRequest", "ProviderSelection", "ProviderType", "RoutingMode"}:
        module = import_module("deep_research_agent.providers.models")
        return getattr(module, name)
    if name == "ProviderRouter":
        module = import_module("deep_research_agent.providers.router")
        return getattr(module, name)
    if name in {"LLMProvider", "TrackedChatAnthropic", "TrackedChatOpenAI", "get_llm"}:
        module = import_module("deep_research_agent.providers.clients")
        return getattr(module, name)
    raise AttributeError(name)
