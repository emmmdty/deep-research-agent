"""Strict contracts crossing the governed tool boundary."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)

from deep_research_agent.kernel.contracts import ArtifactRef


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_JSON_VALUE_ADAPTER = TypeAdapter(JsonValue)


def normalize_json_value(value: Any) -> JsonValue:
    """Validate and normalize a Python value to finite JSON data."""

    normalized = _JSON_VALUE_ADAPTER.validate_python(value)
    json.dumps(normalized, allow_nan=False)
    return normalized


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolSpec(FrozenModel):
    """Policy and execution limits for one registered tool."""

    name: Identifier
    allowed_roles: tuple[Identifier, ...] = Field(min_length=1)
    tenant_scope: Literal["allowlist", "authenticated"] = "allowlist"
    allowed_tenant_ids: tuple[Identifier, ...] = ()
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    max_retries: int = Field(default=0, ge=0)
    retry_safety: Literal["never", "read_only", "adapter_idempotent"] = "never"
    cache_scope: Literal["none", "job"] = "none"
    cache_ttl_seconds: float = Field(default=0.0, ge=0.0)
    max_inline_result_bytes: int = Field(default=64_000, ge=1)

    @model_validator(mode="after")
    def _require_unique_policy_entries(self) -> ToolSpec:
        if len(self.allowed_roles) != len(set(self.allowed_roles)):
            raise ValueError("allowed_roles must be unique")
        if len(self.allowed_tenant_ids) != len(set(self.allowed_tenant_ids)):
            raise ValueError("allowed_tenant_ids must be unique")
        if self.tenant_scope == "allowlist" and not self.allowed_tenant_ids:
            raise ValueError("tenant allowlist must contain at least one tenant")
        if self.tenant_scope == "authenticated" and self.allowed_tenant_ids:
            raise ValueError("authenticated tenant scope cannot include a tenant allowlist")
        if self.max_retries > 0 and self.retry_safety == "never":
            raise ValueError("retries require an explicitly retry-safe tool")
        if self.cache_ttl_seconds > 0 and self.cache_scope != "job":
            raise ValueError("positive cache TTL requires an explicit job cache scope")
        if self.cache_ttl_seconds > 0 and self.retry_safety != "read_only":
            raise ValueError("cached tools must be read-only")
        return self


class ToolInvocation(FrozenModel):
    """One requested tool call from a model worker."""

    invocation_id: Identifier
    tool_name: Identifier
    tenant_id: Identifier
    idempotency_key: Identifier
    arguments: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def _require_json_arguments(cls, value: Any) -> dict[str, JsonValue]:
        if not isinstance(value, dict):
            raise ValueError("tool arguments must be a JSON object")
        try:
            normalized = normalize_json_value(value)
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValueError("tool arguments must contain only finite JSON values") from exc
        if not isinstance(normalized, dict):
            raise ValueError("tool arguments must be a JSON object")
        return normalized


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
    status: Literal["succeeded", "failed", "denied", "execution_uncertain"]
    trust: Literal["untrusted"] = "untrusted"
    output: JsonValue | None = None
    artifact: ArtifactRef | None = None
    error_code: Identifier | None = None
    error: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    from_cache: bool = False
    duplicate: bool = False

    @field_validator("output", mode="before")
    @classmethod
    def _require_json_output(cls, value: Any) -> JsonValue | None:
        if value is None:
            return None
        return normalize_json_value(value)

    @model_validator(mode="after")
    def _validate_payload(self) -> ToolResultEnvelope:
        if self.status == "succeeded" and self.error_code is not None:
            raise ValueError("successful tool results cannot include an error_code")
        if self.status != "succeeded" and self.error_code is None:
            raise ValueError("failed or denied tool results require an error_code")
        if self.output is not None and self.artifact is not None:
            raise ValueError("tool results cannot include inline output and an artifact")
        if self.status == "execution_uncertain" and (
            self.output is not None or self.artifact is not None
        ):
            raise ValueError("uncertain tool results cannot include output")
        return self
