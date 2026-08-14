"""Worker entrypoint for the canonical research-job runtime."""

from __future__ import annotations

import argparse
import importlib
import os
import threading
from uuid import uuid4

from loguru import logger

from configs.settings import get_settings
from deep_research_agent.kernel.contracts import TaskResult, TaskSpec
from deep_research_agent.orchestration.scheduler import ResearchScheduler
from deep_research_agent.orchestration.workers import TaskExecutionContext, WorkerOutput
from deep_research_agent.research_jobs.service import ResearchJobService


def build_parser() -> argparse.ArgumentParser:
    """构建 worker 参数。"""
    parser = argparse.ArgumentParser(description="Phase 02 research job worker")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--workspace-dir", required=True)
    parser.add_argument("--runtime-dirname", default="research_jobs")
    parser.add_argument("--heartbeat-interval-seconds", type=int, default=2)
    parser.add_argument("--stale-timeout-seconds", type=int, default=15)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use the deterministic scheduler fallback explicitly",
    )
    parser.add_argument("--scheduler-factory-path", default=None)
    return parser


class _OfflineTaskWorker:
    async def execute(self, task: TaskSpec, context: TaskExecutionContext) -> WorkerOutput:
        output = {
            "task_id": task.task_id
        } if "task_id" in task.output_schema.get("properties", {}) else {}
        return WorkerOutput(
            result=TaskResult(task_id=task.task_id, job_id=task.job_id, status="completed"),
            output=output,
        )


def build_scheduler_factory(settings, *, offline: bool = False):
    """Build the scheduler composition root; never silently fall back in production."""
    mode = "offline" if offline else getattr(settings, "scheduler_runtime_mode", "production")
    if mode == "offline":
        def offline_factory(**kwargs):
            kwargs.pop("source_profile", None)
            kwargs.pop("policy_overrides", None)
            return ResearchScheduler(worker=_OfflineTaskWorker(), **kwargs)

        return offline_factory

    factory_path = getattr(settings, "scheduler_factory_path", None)
    if not factory_path:
        raise RuntimeError("scheduler factory must be configured for production mode")
    if ":" in factory_path:
        module_name, separator, attribute = factory_path.rpartition(":")
    else:
        module_name, separator, attribute = factory_path.rpartition(".")
    if not separator:
        raise RuntimeError("scheduler factory path must be a dotted import path")
    configured_factory = getattr(importlib.import_module(module_name), attribute, None)
    if not callable(configured_factory):
        raise RuntimeError(f"configured scheduler factory is not callable: {factory_path}")

    def production_factory(**kwargs):
        return configured_factory(settings=settings, **kwargs)

    return production_factory


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    if args.scheduler_factory_path is not None:
        settings = settings.model_copy(update={"scheduler_factory_path": args.scheduler_factory_path})
    service = ResearchJobService(
        workspace_dir=args.workspace_dir,
        runtime_dirname=args.runtime_dirname,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        stale_timeout_seconds=args.stale_timeout_seconds,
        settings=settings,
    )
    job = service.get(args.job_id)
    if job is not None and job.runtime_path == "scheduler-v2":
        service.configure_scheduler_factory(build_scheduler_factory(settings, offline=args.offline))
    lease_id = f"lease-{uuid4().hex[:8]}"
    service.store.acquire_worker_lease(args.job_id, worker_pid=os.getpid(), lease_id=lease_id)

    stop_event = threading.Event()

    def _heartbeat_loop() -> None:
        while not stop_event.wait(args.heartbeat_interval_seconds):
            try:
                service.store.heartbeat(args.job_id, lease_id=lease_id)
            except Exception as exc:  # pragma: no cover - 仅在集成场景出现
                logger.warning("phase2 worker heartbeat 失败: {}", exc)

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    try:
        service.run_job(args.job_id, worker_lease_id=lease_id)
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=1)
        service.store.clear_worker(args.job_id, lease_id=lease_id)


if __name__ == "__main__":
    main()
