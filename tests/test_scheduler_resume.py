"""Tests for scheduler-v2 crash recovery: file journal + resume seeding.

The canonical scheduler-v2 runtime persists every task checkpoint to a
file journal the moment the task completes, so a worker killed mid-run
recovers partial progress instead of restarting the whole DAG.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

import pytest

from deep_research_agent.kernel.contracts import TaskResult
from deep_research_agent.orchestration.events import (
    FileRunJournal,
    RunEvent,
    TaskCheckpoint,
)
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob


def test_file_journal_round_trips_events_and_checkpoints(tmp_path: Path) -> None:
    journal = FileRunJournal(tmp_path / "run.jsonl")
    journal.record_event(
        RunEvent(event_id="e1", job_id="job", sequence=1, event_type="run.started")
    )
    journal.record_checkpoint(
        TaskCheckpoint(
            checkpoint_id="c1",
            job_id="job",
            task_id="t1",
            sequence=1,
            attempt=1,
            result=TaskResult(task_id="t1", job_id="job", status="completed"),
            output={"task_id": "t1"},
            worker_payload={
                "result": {"task_id": "t1", "job_id": "job", "status": "completed"},
                "output": {"task_id": "t1"},
            },
        )
    )

    events, checkpoints = journal.load()

    assert [event.event_type for event in events] == ["run.started"]
    assert [checkpoint.task_id for checkpoint in checkpoints] == ["t1"]
    assert len(journal) == 1


def test_file_journal_latest_checkpoint_wins_per_task(tmp_path: Path) -> None:
    journal = FileRunJournal(tmp_path / "run.jsonl")
    for attempt, status in ((1, "failed"), (2, "completed")):
        journal.record_checkpoint(
            TaskCheckpoint(
                checkpoint_id=f"c{attempt}",
                job_id="job",
                task_id="t1",
                sequence=attempt,
                attempt=attempt,
                result=TaskResult(task_id="t1", job_id="job", status=status),
                output={},
            )
        )

    latest = journal.load_checkpoints()

    assert len(latest) == 1
    assert latest[0].attempt == 2
    assert latest[0].result.status == "completed"


def test_file_journal_skips_corrupt_lines(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        '{"kind": "checkpoint", "record": {"broken": true}}\nnot json\n', encoding="utf-8"
    )

    events, checkpoints = FileRunJournal(path).load()

    assert events == []
    assert checkpoints == []


@pytest.mark.asyncio
async def test_scheduler_resume_from_journal_does_not_redo_completed_tasks(tmp_path: Path) -> None:
    from deep_research_agent.evals.reliability.fault_injection import (
        _chain_dag,
        _CrashWorker,
    )

    dag = _chain_dag()
    journal = FileRunJournal(tmp_path / "journal.jsonl")
    crasher = _CrashWorker()
    run_task = asyncio.create_task(
        ResearchScheduler(worker=crasher, max_workers=1, journal=journal).run(
            SchedulerJob(job_id="crash-resume", tenant_id="default"), dag, {"v": 1}
        )
    )
    while len(journal) < 1:
        await asyncio.sleep(0.005)
    run_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await run_task
    await asyncio.sleep(0.06)

    assert {cp.task_id for cp in journal.load_checkpoints()} == {"task-1"}

    healthy = _CrashWorker()
    result = await ResearchScheduler(
        worker=healthy, max_workers=1, journal=FileRunJournal(tmp_path / "journal.jsonl")
    ).run(
        SchedulerJob(job_id="crash-resume", tenant_id="default"),
        dag,
        {"v": 1},
        seed_checkpoints=journal.load_checkpoints(),
    )

    assert result.status == "completed"
    assert result.resumed_checkpoints == 1
    assert set(healthy.calls) == {"task-2", "task-3"}
    assert result.task_results["task-1"].status == "completed"
    assert all(task_result.status == "completed" for task_result in result.task_results.values())


def test_retryable_failure_checkpoint_keeps_task_pending_and_preserves_attempt(tmp_path: Path):
    """失败但仍在重试预算内的 attempt 必须持久化：恢复后任务保持 pending 且计数不丢。"""
    from deep_research_agent.kernel.contracts import TaskResult, TaskSpec
    from deep_research_agent.orchestration.dag import ResearchDAG
    from deep_research_agent.orchestration.events import FileRunJournal, TaskCheckpoint
    from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
    from deep_research_agent.orchestration.workers import TaskExecutionContext, WorkerOutput

    calls: list[str] = []

    class FlakyWorker:
        async def execute(self, task, context: TaskExecutionContext) -> WorkerOutput:
            calls.append(task.task_id)
            raise RuntimeError("transient boom")

    task = TaskSpec(
        task_id="flaky-task",
        job_id="attempt-durable",
        kind="research",
        role="researcher",
        objective="objective",
        depends_on=[],
        output_schema={"type": "object"},
        budget={"max_tool_calls": 8},
        idempotency_key="attempt-durable:flaky-task",
    )
    dag = ResearchDAG(job_id="attempt-durable", tasks=[task])
    journal = FileRunJournal(tmp_path / "journal.jsonl")

    # 直接构造崩溃现场：attempt 2 失败后进程被杀，只留下了 retryable_failure
    # checkpoint（attempt 计数必须从 2 继续，任务不得被当作终态跳过）。
    journal.record_checkpoint(
        TaskCheckpoint(
            checkpoint_id="attempt-durable:task-checkpoint:000002",
            job_id="attempt-durable",
            task_id="flaky-task",
            sequence=2,
            attempt=2,
            result=TaskResult(
                task_id="flaky-task", job_id="attempt-durable", status="failed", error="boom"
            ),
            output={"retryable_failure": "boom"},
        )
    )

    scheduler = ResearchScheduler(
        worker=FlakyWorker(),
        max_workers=1,
        max_attempts=3,
        journal=journal,
    )
    result = asyncio.run(
        scheduler.run(
            SchedulerJob(job_id="attempt-durable", tenant_id="default"),
            dag,
            {},
            seed_checkpoints=journal.load_checkpoints(),
        )
    )
    assert calls, "恢复后任务必须被重新执行（而非被当作终态跳过）"
    assert result.attempts["flaky-task"] >= 3
    assert result.status == "failed"
