"""Strict contracts crossing the governed tool boundary."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from deep_research_agent.kernel.contracts import ArtifactRef


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolSpec(FrozenModel):
    """Policy and execution limits for one registered tool."""

    name: Identifier
    allowed_roles: tuple[Identifier, ...] = Field(min_length=1)
    allowed_tenant_ids: tuple[Identifier, ...] = ()
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    max_retries: int = Field(default=0, ge=0)
    cache_ttl_seconds: float = Field(default=0.0, ge=0.0)
    max_inline_result_bytes: int = Field(default=64_000, ge=1)

    @model_validator(mode="after")
    def _require_unique_policy_entries(self) -> ToolSpec:
        if len(self.allowed_roles) != len(set(self.allowed_roles)):
            raise ValueError("allowed_roles must be unique")
        if len(self.allowed_tenant_ids) != len(set(self.allowed_tenant_ids)):
            raise ValueError("allowed_tenant_ids must be unique")
        return self


class ToolInvocation(FrozenModel):
    """One requested tool call from a model worker."""

    invocation_id: Identifier
    tool_name: Identifier
    tenant_id: Identifier
    idempotency_key: Identifier
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionContext(FrozenModel):
    """Trusted execution identity supplied by the harness."""

    tenant_id: Identifier
    role: Identifier
    job_id: Identifier


class ToolHandlerContext(FrozenModel):
    """Trusted metadata passed to adapters for tenant-safe, idempotent I/O."""

    invocation_id: Identifier
    idempotency_key: Identifier
    tenant_id: Identifier
    role: Identifier
    job_id: Identifier
    task_id: Identifier


class ToolResultEnvelope(FrozenModel):
    """Untrusted tool data with explicit execution metadata."""

    invocation_id: Identifier
    tool_name: Identifier
    tenant_id: Identifier
    status: Literal["succeeded", "failed", "denied"]
    trust: Literal["untrusted"] = "untrusted"
    output: Any | None = None
    artifact: ArtifactRef | None = None
    error_code: Identifier | None = None
    error: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    from_cache: bool = False
    duplicate: bool = False

    @model_validator(mode="after")
    def _validate_payload(self) -> ToolResultEnvelope:
        if self.status == "succeeded" and self.error_code is not None:
            raise ValueError("successful tool results cannot include an error_code")
        if self.status != "succeeded" and self.error_code is None:
            raise ValueError("failed or denied tool results require an error_code")
        if self.output is not None and self.artifact is not None:
            raise ValueError("tool results cannot include inline output and an artifact")
        return self
