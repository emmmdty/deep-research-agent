"""Framework-independent orchestration for the V2 research runtime."""

from __future__ import annotations

from .dag import ResearchDAG, ResearchPlanner
from .events import CancellationToken, InMemoryRunJournal, RunEvent, TaskCheckpoint
from .reducer import CriticDecision, EvidenceReducer, ReducedEvidence
from .scheduler import ResearchScheduler, RunResult, SchedulerJob
from .workers import TaskExecutionContext, TaskWorker, WorkerOutput

__all__ = [
    "CancellationToken",
    "CriticDecision",
    "EvidenceReducer",
    "InMemoryRunJournal",
    "ReducedEvidence",
    "ResearchDAG",
    "ResearchPlanner",
    "ResearchScheduler",
    "RunEvent",
    "RunResult",
    "SchedulerJob",
    "TaskCheckpoint",
    "TaskExecutionContext",
    "TaskWorker",
    "WorkerOutput",
]
