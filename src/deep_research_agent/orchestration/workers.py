"""Typed worker boundary for model and tool gateway adapters."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import ConfigDict, Field, model_validator

from deep_research_agent.kernel.contracts import StrictModel, TaskResult, TaskSpec
from deep_research_agent.orchestration.reducer import CriticDecision
from deep_research_agent.tool_gateway.models import ToolExecutionContext, ToolInvocation, ToolResultEnvelope


class WorkerOutput(StrictModel):
    """Validated worker envelope plus its declared-schema payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: TaskResult
    output: dict[str, Any] = Field(default_factory=dict)
    spawned_tasks: tuple[TaskSpec, ...] = ()
    critic_decisions: tuple[CriticDecision, ...] = ()

    @model_validator(mode="after")
    def _require_completed_spawn_source(self) -> WorkerOutput:
        if self.spawned_tasks and self.result.status != "completed":
            raise ValueError("only a completed task may emit dynamic tasks")
        return self


@runtime_checkable
class TaskWorker(Protocol):
    async def execute(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput | TaskResult | Mapping[str, Any]: ...


class ModelTaskGateway(Protocol):
    """Provider-neutral model execution boundary implemented outside orchestration."""

    async def execute_task(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput | Mapping[str, Any]: ...


@dataclass(frozen=True)
class TaskExecutionContext:
    job_id: str
    tenant_id: str
    task: TaskSpec
    attempt: int
    config_snapshot: Any
    dependency_results: Mapping[str, WorkerOutput]
    tool_gateway: Any | None = None
    memory: Any | None = None

    async def invoke_tool(self, invocation: ToolInvocation) -> ToolResultEnvelope:
        """Invoke Task 2's governed gateway without importing a provider SDK."""

        if self.tool_gateway is None:
            raise RuntimeError("no tool gateway is configured for this scheduler")
        execution_context = ToolExecutionContext(
            tenant_id=self.tenant_id,
            role=self.task.role,
            job_id=self.job_id,
        )
        fingerprint_payload = {
            "arguments": invocation.arguments,
            "tool_name": invocation.tool_name,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        governed_invocation = invocation.model_copy(
            update={
                "idempotency_key": (
                    f"{self.task.idempotency_key}:{invocation.tool_name}:{fingerprint}"
                )
            }
        )
        return await asyncio.to_thread(
            self.tool_gateway.invoke,
            self.task,
            governed_invocation,
            execution_context,
        )


class GatewayWorker:
    """Small adapter that keeps model framework details behind a gateway protocol."""

    def __init__(self, gateway: ModelTaskGateway) -> None:
        self._gateway = gateway

    async def execute(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput | Mapping[str, Any]:
        return await self._gateway.execute_task(task, context)


def normalize_worker_output(task: TaskSpec, value: WorkerOutput | TaskResult | Mapping[str, Any]) -> WorkerOutput:
    if isinstance(value, WorkerOutput):
        output = value
    elif isinstance(value, TaskResult):
        output = WorkerOutput(result=value, output=value.model_dump(mode="json"))
    elif isinstance(value, Mapping):
        raw = dict(value)
        if "result" in raw:
            output = WorkerOutput.model_validate(raw)
        else:
            output = WorkerOutput(
                result=TaskResult(task_id=task.task_id, job_id=task.job_id, status="completed"),
                output=raw,
            )
    else:
        raise TypeError(f"worker returned unsupported output type: {type(value).__name__}")

    if output.result.task_id != task.task_id or output.result.job_id != task.job_id:
        raise ValueError("worker result identity does not match its task")
    if any(spawned.job_id != task.job_id for spawned in output.spawned_tasks):
        raise ValueError("dynamically spawned tasks must belong to the same job")
    return output
