"""Validated, framework-independent research DAG contracts."""

from __future__ import annotations

import hashlib
import re
from collections import deque
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ConfigDict, Field, model_validator

from deep_research_agent.domain_packs.models import DomainPack
from deep_research_agent.kernel.contracts import ResearchBrief, StrictModel, TaskSpec

# Every researcher task must carry an explicit tool-call budget: the governed
# tool gateway denies any call when ``max_tool_calls`` is missing, so the
# deterministic planner must never emit budget-less research tasks.
_DEFAULT_MAX_TOOL_CALLS_PER_TASK = 16
# Deterministic effort tiers used when settings cannot be resolved; the medium
# tier mirrors the pre-scaling default budget.
_FALLBACK_EFFORT_TIERS = {
    "low": {"max_tool_calls": 8},
    "medium": {"max_tool_calls": 16},
    "high": {"max_tool_calls": 32},
}


class ResearchDAG(StrictModel):
    """One immutable revision of the tasks available to a research run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1)
    tasks: tuple[TaskSpec, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_graph(self) -> ResearchDAG:
        task_by_id = {task.task_id: task for task in self.tasks}
        if len(task_by_id) != len(self.tasks):
            raise ValueError("task ids must be unique")
        if len({task.idempotency_key for task in self.tasks}) != len(self.tasks):
            raise ValueError("task idempotency keys must be unique")
        if any(task.job_id != self.job_id for task in self.tasks):
            raise ValueError("all tasks must belong to the DAG job")

        for task in self.tasks:
            try:
                Draft202012Validator.check_schema(task.output_schema)
            except Exception as exc:
                raise ValueError(f"task {task.task_id!r} has an invalid output schema") from exc
            unknown = set(task.depends_on) - task_by_id.keys()
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"task {task.task_id!r} has unknown dependencies: {names}")

        indegree = dict.fromkeys(task_by_id, 0)
        dependents: dict[str, list[str]] = {task_id: [] for task_id in task_by_id}
        for task in self.tasks:
            indegree[task.task_id] = len(task.depends_on)
            for dependency in task.depends_on:
                dependents[dependency].append(task.task_id)
        ready = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
        visited = 0
        while ready:
            task_id = ready.popleft()
            visited += 1
            for dependent in sorted(dependents[task_id]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
        if visited != len(task_by_id):
            raise ValueError("research DAG contains a dependency cycle")
        return self

    @property
    def task_by_id(self) -> dict[str, TaskSpec]:
        return {task.task_id: task for task in self.tasks}

    def with_tasks(self, tasks: list[TaskSpec] | tuple[TaskSpec, ...]) -> ResearchDAG:
        """Return a validated DAG revision containing newly discovered tasks."""

        current = self.task_by_id
        additions: list[TaskSpec] = []
        for task in tasks:
            existing = current.get(task.task_id)
            if existing is not None:
                if existing != task:
                    raise ValueError(
                        f"dynamic task {task.task_id!r} conflicts with its prior definition"
                    )
                continue
            current[task.task_id] = task
            additions.append(task)
        return ResearchDAG(job_id=self.job_id, tasks=(*self.tasks, *additions))


class ResearchPlanner:
    """Deterministically compile a brief and domain pack into typed tasks."""

    def __init__(self, settings: Any | None = None) -> None:
        self._settings = settings

    def plan(self, brief: ResearchBrief, domain_pack: DomainPack) -> ResearchDAG:
        if brief.domain_pack_id != domain_pack.pack_id:
            raise ValueError("brief domain_pack_id does not match the supplied domain pack")
        objectives = brief.objectives or domain_pack.research_questions or [brief.question]
        effort = str(brief.constraints.get("effort") or "medium")
        budget = self._budget_for_effort(effort)
        tasks = [
            self._research_task(brief, objective, index=index, budget=budget)
            for index, objective in enumerate(objectives, start=1)
        ]
        critic = TaskSpec(
            task_id="critic",
            job_id=brief.job_id,
            kind="critic",
            role="critic",
            objective="Identify semantic disagreements and qualify unsupported conclusions.",
            depends_on=[task.task_id for task in tasks],
            input_artifacts=[],
            output_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
                "additionalProperties": True,
            },
            budget={},
            idempotency_key=f"{brief.job_id}:critic",
        )
        return ResearchDAG(job_id=brief.job_id, tasks=(*tasks, critic))

    def _budget_for_effort(self, effort: str) -> dict[str, int | str]:
        """Resolve the effective effort tier into a task budget.

        Unknown effort values and any settings resolution failure degrade to
        the deterministic medium tier so the planner never emits budget-less
        tasks. The budget carries both ``max_tool_calls`` and the effective
        ``effort`` name, which the model router consumes when it selects a
        per-task chat.
        """
        tiers = _FALLBACK_EFFORT_TIERS
        if self._settings is not None:
            tiers = getattr(self._settings, "effort_tiers", None) or tiers
        tier = tiers.get(effort)
        effective = effort if tier is not None else "medium"
        tier = tier or tiers.get("medium") or {"max_tool_calls": _DEFAULT_MAX_TOOL_CALLS_PER_TASK}
        max_tool_calls = int(tier.get("max_tool_calls") or _DEFAULT_MAX_TOOL_CALLS_PER_TASK)
        return {"max_tool_calls": max_tool_calls, "effort": effective}

    @staticmethod
    def _research_task(
        brief: ResearchBrief,
        objective: str,
        *,
        index: int,
        budget: dict[str, int | str],
    ) -> TaskSpec:
        slug = re.sub(r"[^a-z0-9]+", "-", objective.casefold()).strip("-")[:36]
        if not slug:
            slug = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:12]
        task_id = f"research-{index:02d}-{slug}"
        return TaskSpec(
            task_id=task_id,
            job_id=brief.job_id,
            kind="research",
            role="researcher",
            objective=objective,
            depends_on=[],
            input_artifacts=[],
            output_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
                "additionalProperties": True,
            },
            budget=budget,
            idempotency_key=f"{brief.job_id}:{task_id}",
        )
