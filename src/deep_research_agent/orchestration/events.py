"""Monotonic events, task checkpoints, and cooperative cancellation."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from pydantic import ConfigDict, Field

from deep_research_agent.kernel.contracts import StrictModel, TaskId, TaskResult


class RunEvent(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    task_id: TaskId | None = None
    attempt: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskCheckpoint(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    task_id: TaskId
    sequence: int = Field(ge=1)
    attempt: int = Field(ge=1)
    result: TaskResult
    output: dict[str, Any] = Field(default_factory=dict)


class RunJournal(Protocol):
    """Persistence boundary implemented by Task 5 storage adapters."""

    def record_event(self, event: RunEvent) -> None: ...

    def record_checkpoint(self, checkpoint: TaskCheckpoint) -> None: ...


class InMemoryRunJournal:
    def __init__(self) -> None:
        self.events: list[RunEvent] = []
        self.checkpoints: list[TaskCheckpoint] = []

    def record_event(self, event: RunEvent) -> None:
        self.events.append(event)

    def record_checkpoint(self, checkpoint: TaskCheckpoint) -> None:
        self.checkpoints.append(checkpoint)


class CancellationToken:
    """Cooperative cancellation signal shared by a scheduler and its owner."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()
