"""Shared runner for the external benchmark portfolio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deep_research_agent.evals.external.contracts import BenchmarkRunRequest
from deep_research_agent.evals.external.registry import load_benchmark_runner


def run_external_benchmark(
    *,
    benchmark_name: str,
    output_root: str | Path,
    split: str | None = None,
    subset: str | None = None,
    bucket: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """Run one external benchmark and persist its canonical artifacts."""

    descriptor, runner_fn = load_benchmark_runner(benchmark_name)
    request = BenchmarkRunRequest(
        benchmark_name=benchmark_name,
        output_root=str(Path(output_root).resolve()),
        split=split,
        subset=subset,
        bucket=bucket,
        config_path=config_path or descriptor.config_path,
    )
    return runner_fn(request=request, descriptor=descriptor)
