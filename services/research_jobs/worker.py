"""Phase 02 job worker 入口。"""

from __future__ import annotations

import argparse
import os
import threading
from uuid import uuid4

from loguru import logger

from services.research_jobs.service import ResearchJobService


def build_parser() -> argparse.ArgumentParser:
    """构建 worker 参数。"""
    parser = argparse.ArgumentParser(description="Phase 02 research job worker")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--workspace-dir", required=True)
    parser.add_argument("--runtime-dirname", default="research_jobs")
    parser.add_argument("--heartbeat-interval-seconds", type=int, default=2)
    parser.add_argument("--stale-timeout-seconds", type=int, default=15)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = ResearchJobService(
        workspace_dir=args.workspace_dir,
        runtime_dirname=args.runtime_dirname,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        stale_timeout_seconds=args.stale_timeout_seconds,
    )
    lease_id = f"lease-{uuid4().hex[:8]}"
    service.store.attach_worker(args.job_id, worker_pid=os.getpid(), lease_id=lease_id)

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
        service.run_job(args.job_id)
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=1)
        service.store.clear_worker(args.job_id)


if __name__ == "__main__":
    main()
