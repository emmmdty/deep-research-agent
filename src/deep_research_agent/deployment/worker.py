"""Validate runtime composition and supervise recovery for durable jobs."""

from __future__ import annotations

import argparse
import importlib
import signal
import threading
from pathlib import Path

from configs.settings import Settings, get_settings
from deep_research_agent.model_runtime.registry import CredentialCipher
from deep_research_agent.research_jobs import ResearchJobService


def validate_runtime_configuration(settings: Settings) -> None:
    """Fail closed when a production credential key or scheduler factory is missing."""

    CredentialCipher.from_environment()
    if settings.scheduler_runtime_mode == "offline":
        return
    factory_path = (
        settings.scheduler_factory_path or ""
    ).strip() or "deep_research_agent.agents.factory:build_scheduler_factory"
    module_name, separator, attribute_name = factory_path.replace(":", ".").rpartition(".")
    if not separator:
        raise RuntimeError("SCHEDULER_FACTORY_PATH must be a dotted import path")
    factory = getattr(importlib.import_module(module_name), attribute_name, None)
    if not callable(factory):
        raise RuntimeError(f"configured scheduler factory is not callable: {factory_path}")


def supervise_worker(
    *,
    settings: Settings,
    heartbeat_file: Path,
    interval_seconds: float,
) -> None:
    """Recover stale shared-workspace jobs and expose a container heartbeat."""

    if interval_seconds <= 0:
        raise ValueError("worker interval must be positive")
    validate_runtime_configuration(settings)
    service = ResearchJobService(settings=settings)
    stopped = threading.Event()

    def stop(_signum, _frame) -> None:
        stopped.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
    while not stopped.is_set():
        service.recover_stale_jobs()
        heartbeat_file.touch()
        stopped.wait(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Durable research worker supervisor")
    parser.add_argument("--check", action="store_true", help="validate configuration and exit")
    parser.add_argument("--heartbeat-file", type=Path, default=Path("/tmp/research-worker-health"))
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    args = parser.parse_args()
    settings = get_settings()
    if args.check:
        validate_runtime_configuration(settings)
        return
    supervise_worker(
        settings=settings,
        heartbeat_file=args.heartbeat_file,
        interval_seconds=args.interval_seconds,
    )


if __name__ == "__main__":
    main()


__all__ = ["supervise_worker", "validate_runtime_configuration"]
