"""Source policy data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectorBudget(BaseModel):
    """Connector budget limits for a research job."""

    max_candidates_per_connector: int = Field(default=4, ge=0)
    max_fetches_per_task: int = Field(default=3, ge=0)
    max_total_fetches: int = Field(default=8, ge=0)


class SourcePolicyOverrides(BaseModel):
    """Job-level source policy overrides."""

    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)
    budget: ConnectorBudget | None = Field(default=None)
