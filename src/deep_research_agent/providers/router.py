"""Deterministic provider routing."""

from __future__ import annotations

from deep_research_agent.providers.models import (
    ProviderProfile,
    ProviderRouteRequest,
    ProviderSelection,
    ProviderType,
    RoutingMode,
)


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

        current_family = _provider_family(request.current_provider)
        profile_family = _provider_family(profile.provider_type.value)
        if request.task_role == "judge" and current_family and current_family != profile_family:
            score += 30

        if profile.name == self.settings.get_default_provider_profile_name():
            score += 5

        health_bonus = request.provider_health.get(profile.name)
        if health_bonus is not None:
            score += int(health_bonus * 10)

        return score - profile.priority
