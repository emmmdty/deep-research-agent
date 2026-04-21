"""Provider contracts for Phase 2 routing."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


class RoutingMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ProviderCapabilities(BaseModel):
    reasoning: bool = Field(default=False)
    structured_output: bool = Field(default=False)
    fast: bool = Field(default=False)
    file_understanding: bool = Field(default=False)
    judge_preferred: bool = Field(default=False)


class ProviderProfile(BaseModel):
    name: str = Field(description="Stable profile name")
    provider_type: ProviderType = Field(description="Provider class")
    model: str = Field(description="Default model identifier")
    api_key: str | None = Field(default=None, description="API key or token")
    base_url: str | None = Field(default=None, description="Optional custom base URL")
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=4096)
    enabled: bool = Field(default=True)
    priority: int = Field(default=100, description="Smaller values win tie-breakers")
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderRouteRequest(BaseModel):
    task_role: str = Field(default="planning")
    routing_mode: RoutingMode = Field(default=RoutingMode.AUTO)
    provider_profile: str | None = Field(default=None)
    model_profile: str | None = Field(default=None)
    required_capabilities: list[str] = Field(default_factory=list)
    source_profile: str | None = Field(default=None)
    budget: dict[str, Any] = Field(default_factory=dict)
    latency_target: str = Field(default="balanced")
    current_provider: str | None = Field(default=None)
    provider_health: dict[str, float] = Field(default_factory=dict)


class ProviderSelection(BaseModel):
    profile: ProviderProfile
    routing_mode: RoutingMode
    reason: str
