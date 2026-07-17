"""Strict contracts for versioned model runtime configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType
from typing import Annotated, Literal, Mapping

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    field_serializer,
    model_validator,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenModel(BaseModel):
    """Immutable boundary model with no undeclared fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class EndpointCredentialInput(BaseModel):
    """Write-only credential accepted at the registry boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_id: Identifier
    api_key: SecretStr = Field(exclude=True, repr=False)

    @field_serializer("api_key", when_used="always")
    def _never_serialize_api_key(self, _value: SecretStr) -> None:
        return None


class ModelEndpoint(FrozenModel):
    """One independently configured OpenAI-compatible model endpoint."""

    endpoint_id: Identifier
    base_url: AnyHttpUrl
    model: Identifier
    credential_id: Identifier
    tier: Identifier
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    supports_structured_output: bool = False
    supports_tool_use: bool = False


class AgentRoleProfile(FrozenModel):
    """Ordered, same-tier endpoint chain for one agent role."""

    role: Identifier
    tier: Identifier
    endpoint_ids: tuple[Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_unique_endpoints(self) -> AgentRoleProfile:
        if len(self.endpoint_ids) != len(set(self.endpoint_ids)):
            raise ValueError("role endpoint_ids must be unique")
        return self


class RuntimeConfigVersion(FrozenModel):
    """Immutable model runtime configuration activated as one unit."""

    version_id: Identifier
    endpoints: tuple[ModelEndpoint, ...] = Field(min_length=1)
    role_profiles: tuple[AgentRoleProfile, ...] = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate_references(self) -> RuntimeConfigVersion:
        endpoint_by_id = {endpoint.endpoint_id: endpoint for endpoint in self.endpoints}
        if len(endpoint_by_id) != len(self.endpoints):
            raise ValueError("endpoint_id values must be unique")
        if len({endpoint.credential_id for endpoint in self.endpoints}) != len(self.endpoints):
            raise ValueError("each endpoint requires an independent credential_id")
        if len({profile.role for profile in self.role_profiles}) != len(self.role_profiles):
            raise ValueError("role values must be unique")

        for profile in self.role_profiles:
            for endpoint_id in profile.endpoint_ids:
                endpoint = endpoint_by_id.get(endpoint_id)
                if endpoint is None:
                    raise ValueError(
                        f"role {profile.role!r} references unknown endpoint {endpoint_id!r}"
                    )
                if endpoint.tier != profile.tier:
                    raise ValueError(
                        f"fallback endpoints for role {profile.role!r} must use the same tier"
                    )
        return self


class JobRuntimeSnapshot(FrozenModel):
    """Deeply immutable runtime configuration pinned to one job."""

    job_id: Identifier
    version: RuntimeConfigVersion
    fallback_chains: Mapping[str, tuple[str, ...]]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _freeze_fallback_chains(self) -> JobRuntimeSnapshot:
        frozen = MappingProxyType(
            {role: tuple(endpoint_ids) for role, endpoint_ids in self.fallback_chains.items()}
        )
        object.__setattr__(self, "fallback_chains", frozen)
        return self

    @field_serializer("fallback_chains")
    def _serialize_fallback_chains(
        self,
        value: Mapping[str, tuple[str, ...]],
    ) -> dict[str, tuple[str, ...]]:
        return dict(value)


class ResolvedModelEndpoint(FrozenModel):
    """Actual endpoint and model selected for a role attempt."""

    version_id: Identifier
    role: Identifier
    attempt: int = Field(ge=0)
    endpoint_id: Identifier
    base_url: AnyHttpUrl
    model: Identifier
    credential_id: Identifier
    tier: Identifier
    timeout_seconds: float = Field(gt=0.0)
    supports_structured_output: bool
    supports_tool_use: bool


class ModelCapabilityReport(FrozenModel):
    """Result of probing one configured endpoint."""

    endpoint_id: Identifier
    model: Identifier
    ok: bool
    supports_structured_output: bool = False
    supports_tool_use: bool = False
    error: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _validate_status(self) -> ModelCapabilityReport:
        if self.ok and self.error is not None:
            raise ValueError("successful capability reports cannot include an error")
        if not self.ok and not self.error:
            raise ValueError("failed capability reports require an error")
        return self


class ProbeCapabilities(FrozenModel):
    """Normalized successful response from a capability probe transport."""

    supports_structured_output: bool
    supports_tool_use: bool


class ResolutionRecord(FrozenModel):
    """Audit record of the concrete endpoint selected for an attempt."""

    version_id: Identifier
    job_id: Identifier | None = None
    role: Identifier
    attempt: int = Field(ge=0)
    endpoint_id: Identifier
    model: Identifier
    outcome: Literal["resolved"] = "resolved"
