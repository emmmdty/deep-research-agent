"""Policy 数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectorBudget(BaseModel):
    """connector 预算。"""

    max_candidates_per_connector: int = Field(default=4, ge=0)
    max_fetches_per_task: int = Field(default=3, ge=0)
    max_total_fetches: int = Field(default=8, ge=0)


class SourcePolicyOverrides(BaseModel):
    """job 级策略覆盖。"""

    allow_domains: list[str] = Field(default_factory=list)
    deny_domains: list[str] = Field(default_factory=list)
    budget: ConnectorBudget | None = Field(default=None)
