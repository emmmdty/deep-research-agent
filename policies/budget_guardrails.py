"""Budget guardrails。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from policies.models import ConnectorBudget


class BudgetUsage(BaseModel):
    """当前 budget 使用量。"""

    total_fetches: int = Field(default=0, ge=0)
    fetches_for_task: int = Field(default=0, ge=0)


class BudgetGuard:
    """用于 collecting 阶段的 budget 控制。"""

    def __init__(self, budget: ConnectorBudget, usage: BudgetUsage | None = None) -> None:
        self.budget = budget
        self.usage = usage or BudgetUsage()

    def remaining_candidate_limit(self) -> int:
        return self.budget.max_candidates_per_connector

    def can_fetch(self) -> bool:
        return (
            self.usage.total_fetches < self.budget.max_total_fetches
            and self.usage.fetches_for_task < self.budget.max_fetches_per_task
        )

    def record_fetch(self) -> None:
        self.usage.total_fetches += 1
        self.usage.fetches_for_task += 1
