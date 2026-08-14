"""Async dependency scheduler with bounded fan-out and branch-local retry."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema.validators import validator_for
from pydantic import ConfigDict, Field

from deep_research_agent.kernel.contracts import StrictModel, TaskResult, TaskSpec
from deep_research_agent.orchestration.dag import ResearchDAG
from deep_research_agent.orchestration.events import (
    CancellationToken,
    InMemoryRunJournal,
    RunEvent,
    RunJournal,
    TaskCheckpoint,
)
from deep_research_agent.orchestration.workers import (
    TaskExecutionContext,
    TaskWorker,
    WorkerOutput,
    normalize_worker_output,
)
from deep_research_agent.orchestration.reducer import CriticDecision


class DynamicTaskConflict(ValueError):
    """A dynamic task id was redeclared with a different immutable definition."""


class SchedulerJob(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1)
    tenant_id: str = Field(default="default", min_length=1)
    cancel_requested: bool = False


class RunResult(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str
    status: Literal["completed", "failed", "cancelled"]
    task_results: dict[str, TaskResult]
    task_outputs: dict[str, dict[str, Any]]
    attempts: dict[str, int]
    events: list[RunEvent]
    checkpoints: list[TaskCheckpoint]
    config_snapshot: Any
    critic_decisions: list[CriticDecision] = Field(default_factory=list)
    resumed_checkpoints: int = 0


class ResearchScheduler:
    """Own all lifecycle transitions for one typed research DAG."""

    def __init__(
        self,
        *,
        worker: TaskWorker,
        max_workers: int = 4,
        max_attempts: int = 2,
        cancellation_token: CancellationToken | None = None,
        cancellation_check: Callable[[], bool] | None = None,
        cancellation_poll_seconds: float = 0.05,
        journal: RunJournal | None = None,
        tool_gateway: Any | None = None,
    ) -> None:
        if not 1 <= max_workers <= 8:
            raise ValueError("max_workers must be between 1 and at most 8")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if cancellation_poll_seconds <= 0:
            raise ValueError("cancellation_poll_seconds must be positive")
        self._worker = worker
        self._max_workers = max_workers
        self._max_attempts = max_attempts
        self._token = cancellation_token or CancellationToken()
        self._cancellation_check = cancellation_check
        self._cancellation_poll_seconds = cancellation_poll_seconds
        self._journal = journal if journal is not None else InMemoryRunJournal()
        self._tool_gateway = tool_gateway

    async def run(
        self,
        job: SchedulerJob | Mapping[str, Any] | Any,
        dag: ResearchDAG,
        config_snapshot: Any,
        *,
        seed_checkpoints: Sequence[TaskCheckpoint] | None = None,
    ) -> RunResult:
        job_id, tenant_id, initial_cancelled = self._job_identity(job)
        if dag.job_id != job_id:
            raise ValueError("job and DAG identifiers do not match")

        events: list[RunEvent] = []
        checkpoints: list[TaskCheckpoint] = []
        task_by_id = dag.task_by_id
        declared_tasks = dict(task_by_id)
        pending = set(task_by_id)
        running: dict[asyncio.Task[WorkerOutput], str] = {}
        outputs: dict[str, WorkerOutput] = {}
        results: dict[str, TaskResult] = {}
        attempts: dict[str, int] = {task_id: 0 for task_id in task_by_id}
        failed: set[str] = set()
        dag, resumed = self._replay_seeded_checkpoints(
            seed_checkpoints or [],
            dag,
            outputs,
            results,
            attempts,
            failed,
            declared_tasks,
        )
        task_by_id = dag.task_by_id

        self._emit(events, job_id, "run.started", payload={"task_count": len(task_by_id)})
        if initial_cancelled:
            self._token.cancel()
        if resumed:
            pending = set(task_by_id) - set(results)
            self._emit(
                events,
                job_id,
                "run.resumed",
                payload={"seeded_tasks": sorted(outputs) if outputs else []},
            )

        while pending or running:
            if self._is_cancelled():
                await self._cancel_remaining(
                    job_id, pending, running, task_by_id, results, outputs, attempts, checkpoints, events
                )
                return self._result(
                    job_id, "cancelled", results, outputs, attempts, events, checkpoints, config_snapshot,
                    resumed_checkpoints=resumed,
                )

            blocked = sorted(
                task_id
                for task_id in pending
                if set(task_by_id[task_id].depends_on) & failed
            )
            for task_id in blocked:
                pending.remove(task_id)
                failed.add(task_id)
                result = TaskResult(
                    task_id=task_id,
                    job_id=job_id,
                    status="failed",
                    error="dependency failed",
                )
                results[task_id] = result
                self._checkpoint(checkpoints, job_id, task_by_id[task_id], max(attempts[task_id], 1), result, {})
                self._emit(events, job_id, "task.blocked", task_id=task_id, payload={"reason": "dependency_failed"})

            ready = sorted(
                task_id
                for task_id in pending
                if set(task_by_id[task_id].depends_on) <= outputs.keys()
            )
            while ready and len(running) < self._max_workers:
                task_id = ready.pop(0)
                pending.remove(task_id)
                task = task_by_id[task_id]
                attempts[task_id] += 1
                attempt = attempts[task_id]
                context = TaskExecutionContext(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    task=task,
                    attempt=attempt,
                    config_snapshot=config_snapshot,
                    dependency_results={dependency: outputs[dependency] for dependency in task.depends_on},
                    tool_gateway=self._tool_gateway,
                )
                future = asyncio.create_task(self._execute(task, context))
                running[future] = task_id
                self._emit(events, job_id, "task.started", task_id=task_id, attempt=attempt)

            if not running:
                if pending:
                    raise RuntimeError("scheduler reached a non-terminal DAG state without ready tasks")
                break

            cancellation_wait = asyncio.create_task(self._token.wait())
            done, _ = await asyncio.wait(
                [*running, cancellation_wait],
                timeout=(
                    self._cancellation_poll_seconds
                    if self._cancellation_check is not None
                    else None
                ),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_wait in done or self._is_cancelled():
                cancellation_wait.cancel()
                await asyncio.gather(cancellation_wait, return_exceptions=True)
                await self._cancel_remaining(
                    job_id, pending, running, task_by_id, results, outputs, attempts, checkpoints, events
                )
                return self._result(
                    job_id, "cancelled", results, outputs, attempts, events, checkpoints, config_snapshot,
                    resumed_checkpoints=resumed,
                )
            cancellation_wait.cancel()
            await asyncio.gather(cancellation_wait, return_exceptions=True)
            if not done:
                continue

            completed_futures = sorted(
                (future for future in done if future in running), key=lambda future: running[future]
            )
            for future in completed_futures:
                task_id = running.pop(future)
                task = task_by_id[task_id]
                attempt = attempts[task_id]
                try:
                    output = future.result()
                    if output.result.status != "completed":
                        raise RuntimeError(output.result.error or f"worker returned {output.result.status}")
                    self._validate_output_schema(task, output.output)
                    if output.spawned_tasks:
                        new_tasks: list[TaskSpec] = []
                        candidate_by_id: dict[str, TaskSpec] = {}
                        for spawned in output.spawned_tasks:
                            existing = declared_tasks.get(spawned.task_id)
                            candidate = candidate_by_id.get(spawned.task_id)
                            if candidate is not None:
                                existing = candidate
                            if existing is not None:
                                if existing != spawned:
                                    raise DynamicTaskConflict(
                                        f"conflicting dynamic task definition for {spawned.task_id!r}"
                                    )
                                continue
                            candidate_by_id[spawned.task_id] = spawned
                            new_tasks.append(spawned)
                        if new_tasks:
                            dag = dag.with_tasks(new_tasks)
                            task_by_id = dag.task_by_id
                            declared_tasks.update(candidate_by_id)
                        for spawned in new_tasks:
                            if spawned.task_id not in results and spawned.task_id not in outputs:
                                pending.add(spawned.task_id)
                                attempts.setdefault(spawned.task_id, 0)
                        self._emit(
                            events,
                            job_id,
                            "task.fan_out",
                            task_id=task_id,
                            attempt=attempt,
                            payload={"spawned_task_ids": sorted(item.task_id for item in output.spawned_tasks)},
                        )
                except Exception as exc:
                    error = self._error_message(exc)
                    if attempt < self._max_attempts and not isinstance(exc, DynamicTaskConflict):
                        pending.add(task_id)
                        self._emit(
                            events,
                            job_id,
                            "task.retry_scheduled",
                            task_id=task_id,
                            attempt=attempt,
                            payload={"error": error},
                        )
                        continue
                    result = TaskResult(
                        task_id=task_id,
                        job_id=job_id,
                        status="failed",
                        error=error,
                    )
                    results[task_id] = result
                    failed.add(task_id)
                    self._checkpoint(checkpoints, job_id, task, attempt, result, {})
                    self._emit(
                        events,
                        job_id,
                        "task.failed",
                        task_id=task_id,
                        attempt=attempt,
                        payload={"error": error},
                    )
                    continue

                outputs[task_id] = output
                results[task_id] = output.result
                self._checkpoint(
                    checkpoints,
                    job_id,
                    task,
                    attempt,
                    output.result,
                    output.output,
                    worker_payload=output.model_dump(mode="json"),
                )
                self._emit(events, job_id, "task.completed", task_id=task_id, attempt=attempt)

        status: Literal["completed", "failed"] = "failed" if failed else "completed"
        self._emit(events, job_id, f"run.{status}", payload={"task_count": len(results)})
        return self._result(
            job_id, status, results, outputs, attempts, events, checkpoints, config_snapshot,
            resumed_checkpoints=resumed,
        )

    async def _execute(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput:
        raw = await self._worker.execute(task, context)
        return normalize_worker_output(task, raw)

    async def _cancel_remaining(
        self,
        job_id: str,
        pending: set[str],
        running: dict[asyncio.Task[WorkerOutput], str],
        task_by_id: dict[str, TaskSpec],
        results: dict[str, TaskResult],
        outputs: dict[str, WorkerOutput],
        attempts: dict[str, int],
        checkpoints: list[TaskCheckpoint],
        events: list[RunEvent],
    ) -> None:
        task_ids = set(pending) | set(running.values())
        for future in running:
            future.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        pending.clear()
        running.clear()
        for task_id in sorted(task_ids):
            if task_id in results:
                continue
            result = TaskResult(task_id=task_id, job_id=job_id, status="cancelled", error="run cancelled")
            results[task_id] = result
            task_attempt = attempts.get(task_id, 0)
            # Never fabricate an attempt for a task that did not start: the
            # attempt counter records real executions only, so a resumed run
            # replays cancelled tasks with a fresh budget.
            self._checkpoint(checkpoints, job_id, task_by_id[task_id], max(task_attempt, 1), result, {})
            self._emit(events, job_id, "task.cancelled", task_id=task_id, attempt=max(task_attempt, 1))
        self._emit(events, job_id, "run.cancelled", payload={"task_count": len(results)})

    @staticmethod
    def _replay_seeded_checkpoints(
        seed_checkpoints: Sequence[TaskCheckpoint],
        dag: ResearchDAG,
        outputs: dict[str, WorkerOutput],
        results: dict[str, TaskResult],
        attempts: dict[str, int],
        failed: set[str],
        declared_tasks: dict[str, TaskSpec],
    ) -> tuple[ResearchDAG, int]:
        """Replay persisted checkpoints so a crashed run continues, not restarts.

        Completed checkpoints restore the full worker payload (outputs and any
        dynamically spawned tasks); failed checkpoints stay failed; cancelled
        checkpoints are NOT restored as terminal results — a cancelled task
        never produced output, so on resume it is re-run with a fresh attempt
        budget. Returns the (possibly extended) DAG and the number of seeded
        checkpoints.
        """

        if not seed_checkpoints:
            return dag, 0
        resumed = 0
        for checkpoint in sorted(seed_checkpoints, key=lambda item: item.sequence):
            task_id = checkpoint.task_id
            if task_id not in declared_tasks:
                # A stale checkpoint for a task that is not in the current DAG
                # (nor declared by a replayed spawner) must not pollute the run.
                continue
            attempts[task_id] = max(attempts.get(task_id, 0), checkpoint.attempt)
            if checkpoint.result.status == "completed" and checkpoint.worker_payload:
                worker = WorkerOutput.model_validate(checkpoint.worker_payload)
                outputs[task_id] = worker
                results[task_id] = worker.result
                for spawned in worker.spawned_tasks:
                    if spawned.task_id not in declared_tasks:
                        dag = dag.with_tasks([spawned])
                        declared_tasks[spawned.task_id] = spawned
                        attempts.setdefault(spawned.task_id, 0)
                resumed += 1
            elif checkpoint.result.status == "failed":
                results[task_id] = checkpoint.result
                failed.add(task_id)
                resumed += 1
            elif checkpoint.result.status == "cancelled":
                # Cancellation is not a terminal outcome: the task produced no
                # output and its dependents were never unblocked. Reset the
                # attempt budget and leave the task pending so it is re-run.
                attempts[task_id] = 0
                resumed += 1
        return dag, resumed

    def _emit(
        self,
        events: list[RunEvent],
        job_id: str,
        event_type: str,
        *,
        task_id: str | None = None,
        attempt: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        sequence = len(events) + 1
        event = RunEvent(
            event_id=f"{job_id}:event:{sequence:06d}",
            job_id=job_id,
            sequence=sequence,
            event_type=event_type,
            task_id=task_id,
            attempt=attempt,
            payload=payload or {},
        )
        self._journal.record_event(event)
        events.append(event)

    def _checkpoint(
        self,
        checkpoints: list[TaskCheckpoint],
        job_id: str,
        task: TaskSpec,
        attempt: int,
        result: TaskResult,
        output: dict[str, Any],
        *,
        worker_payload: dict[str, Any] | None = None,
    ) -> None:
        sequence = len(checkpoints) + 1
        checkpoint = TaskCheckpoint(
            checkpoint_id=f"{job_id}:task-checkpoint:{sequence:06d}",
            job_id=job_id,
            task_id=task.task_id,
            sequence=sequence,
            attempt=attempt,
            result=result,
            output=output,
            worker_payload=worker_payload,
        )
        self._journal.record_checkpoint(checkpoint)
        checkpoints.append(checkpoint)

    def _is_cancelled(self) -> bool:
        return self._token.cancelled or bool(self._cancellation_check and self._cancellation_check())

    @staticmethod
    def _validate_output_schema(task: TaskSpec, output: dict[str, Any]) -> None:
        validator = validator_for(task.output_schema)
        try:
            validator(task.output_schema).validate(output)
        except JsonSchemaValidationError as exc:
            raise ValueError(f"worker output schema validation failed: {exc.message}") from exc

    @staticmethod
    def _error_message(exc: Exception) -> str:
        message = str(exc) or type(exc).__name__
        return message if "output schema" in message else f"task execution failed: {message}"

    @staticmethod
    def _job_identity(job: SchedulerJob | Mapping[str, Any] | Any) -> tuple[str, str, bool]:
        if isinstance(job, Mapping):
            job_id = str(job.get("job_id") or "")
            tenant_id = str(job.get("tenant_id") or "default")
            cancelled = bool(job.get("cancel_requested", False))
        else:
            job_id = str(getattr(job, "job_id", ""))
            metadata = getattr(job, "metadata", {}) or {}
            tenant_id = str(getattr(job, "tenant_id", "") or metadata.get("tenant_id") or "default")
            cancelled = bool(getattr(job, "cancel_requested", False))
        if not job_id:
            raise ValueError("scheduler job requires a job_id")
        return job_id, tenant_id, cancelled

    @staticmethod
    def _result(
        job_id: str,
        status: Literal["completed", "failed", "cancelled"],
        results: dict[str, TaskResult],
        outputs: dict[str, WorkerOutput],
        attempts: dict[str, int],
        events: list[RunEvent],
        checkpoints: list[TaskCheckpoint],
        config_snapshot: Any,
        *,
        resumed_checkpoints: int = 0,
    ) -> RunResult:
        decisions: dict[str, CriticDecision] = {}
        for output in outputs.values():
            for decision in output.critic_decisions:
                existing = decisions.get(decision.decision_id)
                if existing is not None and existing != decision:
                    raise ValueError(f"conflicting critic decision definition for {decision.decision_id!r}")
                decisions[decision.decision_id] = decision
        return RunResult(
            job_id=job_id,
            status=status,
            task_results={key: results[key] for key in sorted(results)},
            task_outputs={key: outputs[key].output for key in sorted(outputs)},
            attempts={key: attempts[key] for key in sorted(attempts)},
            events=events,
            checkpoints=checkpoints,
            critic_decisions=[decisions[key] for key in sorted(decisions)],
            config_snapshot=config_snapshot,
            resumed_checkpoints=resumed_checkpoints,
        )
