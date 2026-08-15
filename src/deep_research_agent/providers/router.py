"""Deterministic provider routing."""

from __future__ import annotations

from typing import Any

from deep_research_agent.providers.models import (
    ProviderProfile,
    ProviderRouteRequest,
    ProviderSelection,
    ProviderType,
    RoutingMode,
)

DEFAULT_PROVIDER_BONUS = 25


class RoutedSettings:
    """Settings view pinned to a routed provider profile.

    ``LLMChat`` resolves credentials through ``get_llm_config()``; this adapter
    swaps in the routed profile while delegating every other attribute to the
    original settings object. Constructing the view is side-effect free, so the
    caller may create it in any thread and hand it to a chat built later.
    """

    def __init__(self, settings: Any, profile: ProviderProfile) -> None:
        self._settings = settings
        self._profile = profile

    def get_llm_config(self) -> dict[str, Any]:
        return {
            "api_key": self._profile.api_key or "",
            "base_url": self._profile.base_url or "",
            "model": self._profile.model,
            "temperature": self._profile.temperature,
            "max_tokens": self._profile.max_tokens,
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._settings, name)


def _provider_family(provider_name_or_type: str | None) -> str | None:
    if not provider_name_or_type:
        return None
    if provider_name_or_type in {ProviderType.OPENAI.value, ProviderType.OPENAI_COMPATIBLE.value, "openai"}:
        return "openai"
    if provider_name_or_type in {
        ProviderType.ANTHROPIC.value,
        ProviderType.ANTHROPIC_COMPATIBLE.value,
        "anthropic",
    }:
        return "anthropic"
    return provider_name_or_type


class ProviderRouter:
    """Routes model requests to concrete provider profiles."""

    def __init__(self, settings) -> None:
        self.settings = settings
        self._profiles = settings.get_provider_profiles()

    @property
    def profiles(self) -> dict[str, ProviderProfile]:
        return dict(self._profiles)

    def route(self, request: ProviderRouteRequest) -> ProviderSelection:
        if request.routing_mode == RoutingMode.MANUAL:
            return self._route_manual(request)
        return self._route_auto(request)

    def route_for_role(self, role: str, *, effort: str = "medium") -> ProviderSelection:
        """Resolve the model for an agent role, deterministically.

        Explicit ``strong_role_models`` / ``cheap_role_models`` overrides win
        first; anything else falls back to the default provider profile. The
        effort tier shapes the fallback: ``low`` may downgrade to an enabled
        fast-capable profile when a cheaper option exists, while ``medium`` and
        ``high`` always use the quality default profile (the default is the
        strongest configured model; effort scaling's other lever is the tool
        budget written by the planner). When the model router is disabled the
        call degrades to a plain manual default-profile route.
        """
        if not getattr(self.settings, "model_router_enabled", True):
            return self._route_manual(ProviderRouteRequest(task_role=role))
        default_profile = self._profiles[self.settings.get_default_provider_profile_name()]
        override = self._role_model_override(role)
        if override:
            profile = default_profile.model_copy(update={"model": override})
            model_name = override
        else:
            profile = self._profile_for_effort(effort, default_profile)
            model_name = profile.model
        return ProviderSelection(
            profile=profile,
            routing_mode=RoutingMode.MANUAL,
            reason=f"role_routing:{role}:{model_name}",
        )

    def _profile_for_effort(
        self, effort: str, default_profile: ProviderProfile
    ) -> ProviderProfile:
        """Pick a deterministic profile for the effort tier; default when N/A."""
        if effort == "low":
            matches = [
                profile
                for profile in self._profiles.values()
                if profile.enabled and getattr(profile.capabilities, "fast", False)
            ]
            if not matches:
                return default_profile
            matches.sort(
                key=lambda profile: (profile.name != default_profile.name, profile.name)
            )
            return matches[0]
        return default_profile

    def _role_model_override(self, role: str) -> str | None:
        strong = getattr(self.settings, "strong_role_models", None) or {}
        cheap = getattr(self.settings, "cheap_role_models", None) or {}
        override = str(strong.get(role) or cheap.get(role) or "")
        return override.strip() or None

    def _route_manual(self, request: ProviderRouteRequest) -> ProviderSelection:
        profile_name = request.provider_profile or self.settings.get_default_provider_profile_name()
        profile = self._profiles[profile_name]
        return ProviderSelection(
            profile=profile,
            routing_mode=RoutingMode.MANUAL,
            reason=f"manual:{profile_name}",
        )

    def _route_auto(self, request: ProviderRouteRequest) -> ProviderSelection:
        candidates = [profile for profile in self._profiles.values() if profile.enabled]
        if not candidates:
            raise ValueError("No enabled provider profiles are available")

        ranked = sorted(
            candidates,
            key=lambda profile: (
                self._score_profile(profile, request),
                -profile.priority,
                profile.name,
            ),
            reverse=True,
        )
        winner = ranked[0]
        return ProviderSelection(
            profile=winner,
            routing_mode=RoutingMode.AUTO,
            reason=f"auto:{request.task_role}:{winner.name}",
        )

    def _score_profile(self, profile: ProviderProfile, request: ProviderRouteRequest) -> int:
        score = 0
        caps = profile.capabilities

        for capability_name in request.required_capabilities:
            if not getattr(caps, capability_name, False):
                return -10_000
            score += 10

        if request.task_role in {"planning", "audit_assist"} and caps.reasoning:
            score += 60
        if request.task_role in {"query_rewrite", "extraction"} and caps.structured_output:
            score += 40
        if request.task_role == "synthesis" and caps.reasoning:
            score += 35
        if request.task_role == "judge" and caps.judge_preferred:
            score += 45
        if request.task_role == "judge" and caps.reasoning:
            score += 10

        if request.latency_target in {"low", "fast"} and caps.fast:
            score += 20
        if request.latency_target == "quality" and caps.reasoning:
            score += 10
        if request.effort == "low" and caps.fast:
            score += 15

        current_family = _provider_family(request.current_provider)
        profile_family = _provider_family(profile.provider_type.value)
        if request.task_role == "judge" and current_family and current_family != profile_family:
            score += 30

        if profile.name == self.settings.get_default_provider_profile_name():
            score += DEFAULT_PROVIDER_BONUS

        health_bonus = request.provider_health.get(profile.name)
        if health_bonus is not None:
            score += int(health_bonus * 10)

        return score - profile.priority
