"""Monotonic events, task checkpoints, and cooperative cancellation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
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
    worker_payload: dict[str, Any] | None = Field(default=None)


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


class FileRunJournal:
    """Append-only journal that survives a worker crash.

    Every event and checkpoint is flushed to a JSONL file the moment the
    scheduler records it, so a scheduler-v2 worker killed mid-run leaves a
    recoverable partial state behind. ``load`` replays the records in order;
    duplicate checkpoints for the same task keep the highest sequence.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def record_event(self, event: RunEvent) -> None:
        self._append("event", event.model_dump(mode="json"))

    def record_checkpoint(self, checkpoint: TaskCheckpoint) -> None:
        self._append("checkpoint", checkpoint.model_dump(mode="json"))

    def _append(self, kind: str, record: dict[str, Any]) -> None:
        line = json.dumps({"kind": kind, "record": record}, ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def load(self) -> tuple[list[RunEvent], list[TaskCheckpoint]]:
        events: list[RunEvent] = []
        checkpoints: list[TaskCheckpoint] = []
        if not self._path.exists():
            return events, checkpoints
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            record = payload.get("record")
            if not isinstance(record, dict):
                continue
            kind = payload.get("kind")
            if kind == "event":
                try:
                    events.append(RunEvent.model_validate(record))
                except Exception:  # noqa: BLE001 - corrupt journal lines must not block recovery
                    continue
            elif kind == "checkpoint":
                try:
                    checkpoints.append(TaskCheckpoint.model_validate(record))
                except Exception:  # noqa: BLE001
                    continue
        return events, checkpoints

    def load_checkpoints(self) -> list[TaskCheckpoint]:
        """Per-task latest checkpoint, in journal order (chronological).

        Journal lines are chronological (append order); a later checkpoint for
        the same task overwrites an earlier one even when the in-memory
        sequence counters restarted after a resume.
        """

        _, checkpoints = self.load()
        by_task: dict[str, TaskCheckpoint] = {}
        for checkpoint in checkpoints:
            by_task[checkpoint.task_id] = checkpoint
        return [by_task[task_id] for task_id in sorted(by_task)]

    def __len__(self) -> int:
        _, checkpoints = self.load()
        return len(checkpoints)


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
