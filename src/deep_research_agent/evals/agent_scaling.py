"""Deterministic 1/2/4/8-agent scaling harness over a frozen input."""

from __future__ import annotations

import argparse
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

WorkerCount = Literal[1, 2, 4, 8]
WORKER_COUNTS: tuple[WorkerCount, ...] = (1, 2, 4, 8)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenScalingInput(StrictModel):
    """Identity of a workload that all scaling variants must share."""

    input_id: str = Field(min_length=1)
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_claim_count: int = Field(gt=0)


class AgentScalingResult(StrictModel):
    """Resource and quality result for one worker count."""

    worker_count: WorkerCount
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_score: float = Field(ge=0, le=1)
    elapsed_ms: float = Field(ge=0)
    total_tokens: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    errors: tuple[str, ...] = ()

    @property
    def error_count(self) -> int:
        return len(self.errors)


class AgentScalingReport(StrictModel):
    """All bounded worker variants over one manifest."""

    mode: Literal["offline", "live"]
    input_id: str
    results: tuple[AgentScalingResult, ...]


class ScalingExecutor(Protocol):
    def __call__(
        self,
        frozen_input: FrozenScalingInput,
        worker_count: WorkerCount,
    ) -> AgentScalingResult:
        """Run one worker-count variant."""


def _offline_executor(
    frozen_input: FrozenScalingInput,
    worker_count: WorkerCount,
) -> AgentScalingResult:
    quality_by_workers = {1: 0.72, 2: 0.82, 4: 0.91, 8: 0.91}
    elapsed_by_workers = {1: 8_000.0, 2: 4_500.0, 4: 2_800.0, 8: 2_500.0}
    return AgentScalingResult(
        worker_count=worker_count,
        manifest_hash=frozen_input.manifest_hash,
        quality_score=quality_by_workers[worker_count],
        elapsed_ms=elapsed_by_workers[worker_count],
        total_tokens=frozen_input.expected_claim_count * (120 + 8 * worker_count),
        tool_calls=frozen_input.expected_claim_count + worker_count,
    )


def run_agent_scaling(
    frozen_input: FrozenScalingInput,
    *,
    executor: ScalingExecutor | None = None,
    live: bool = False,
) -> AgentScalingReport:
    """Execute every supported worker count without changing the input manifest."""

    if live and executor is None:
        raise ValueError("live scaling requires an explicitly configured executor")
    selected_executor = executor or _offline_executor
    results = tuple(selected_executor(frozen_input, count) for count in WORKER_COUNTS)
    if any(item.manifest_hash != frozen_input.manifest_hash for item in results):
        raise ValueError("all scaling results must use the frozen input manifest")
    if tuple(item.worker_count for item in results) != WORKER_COUNTS:
        raise ValueError("scaling results must cover 1, 2, 4, and 8 workers in order")
    return AgentScalingReport(
        mode="live" if live else "offline",
        input_id=frozen_input.input_id,
        results=results,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic agent scaling probes")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = run_agent_scaling(
        FrozenScalingInput(
            input_id="trusted-scientific-research-v1",
            manifest_hash="0" * 64,
            expected_claim_count=12,
        )
    )
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        for result in report.results:
            print(
                f"workers={result.worker_count} quality={result.quality_score:.2f} "
                f"elapsed_ms={result.elapsed_ms:.0f} errors={result.error_count}"
            )


if __name__ == "__main__":
    main()


__all__ = [
    "WORKER_COUNTS",
    "AgentScalingReport",
    "AgentScalingResult",
    "FrozenScalingInput",
    "ScalingExecutor",
    "run_agent_scaling",
]
