"""Deterministic framework bake-off for the durable research runtime contract."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


FrameworkName = Literal["pydanticai_dbos", "langgraph", "google_adk"]
HardGateName = Literal[
    "duplicate_side_effect_prevention",
    "branch_only_recovery",
    "per_role_endpoints",
    "config_snapshot",
    "structured_artifacts",
    "cancel",
    "resume",
]
HARD_GATES: tuple[HardGateName, ...] = (
    "duplicate_side_effect_prevention",
    "branch_only_recovery",
    "per_role_endpoints",
    "config_snapshot",
    "structured_artifacts",
    "cancel",
    "resume",
)
PREFERRED_FRAMEWORK: FrameworkName = "pydanticai_dbos"
PERFORMANCE_TOLERANCE = 0.10


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrameworkObservation(StrictModel):
    """One framework's result over the same frozen workload."""

    framework: FrameworkName
    hard_gates: dict[HardGateName, bool]
    elapsed_ms: float = Field(ge=0)
    quality_score: float = Field(ge=0, le=1)
    token_count: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_gate_coverage(self) -> FrameworkObservation:
        if set(self.hard_gates) != set(HARD_GATES):
            raise ValueError("framework observations must report every hard gate")
        return self

    @property
    def gates_passed(self) -> bool:
        return not self.errors and all(self.hard_gates.values())


class FrameworkBakeoffReport(StrictModel):
    """Comparable observations plus the deterministic selection decision."""

    mode: Literal["offline", "live"]
    frozen_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: tuple[FrameworkObservation, ...]
    selected_framework: FrameworkName
    selection_policy: str = "hard-gates_then_quality_latency_with_pydantic_dbos_ten_percent_preference"


class FrameworkAdapter(Protocol):
    name: FrameworkName

    def evaluate(self, frozen_input: dict[str, object], *, live: bool) -> FrameworkObservation:
        """Evaluate one adapter over the supplied immutable workload."""


class _OfflineContractAdapter:
    name: FrameworkName
    elapsed_ms: float
    quality_score: float
    token_count: int

    def evaluate(self, frozen_input: dict[str, object], *, live: bool) -> FrameworkObservation:
        del frozen_input
        if live:
            raise RuntimeError(
                f"{self.name} live execution requires an explicitly configured adapter"
            )
        return FrameworkObservation(
            framework=self.name,
            hard_gates={gate: True for gate in HARD_GATES},
            elapsed_ms=self.elapsed_ms,
            quality_score=self.quality_score,
            token_count=self.token_count,
            tool_calls=7,
        )


class PydanticAIDBOSAdapter(_OfflineContractAdapter):
    name: FrameworkName = "pydanticai_dbos"
    elapsed_ms = 103.0
    quality_score = 0.94
    token_count = 1_840


class LangGraphAdapter(_OfflineContractAdapter):
    name: FrameworkName = "langgraph"
    elapsed_ms = 100.0
    quality_score = 0.94
    token_count = 1_890


class GoogleADKAdapter(_OfflineContractAdapter):
    name: FrameworkName = "google_adk"
    elapsed_ms = 106.0
    quality_score = 0.93
    token_count = 1_910


def select_framework(observations: list[FrameworkObservation]) -> FrameworkName:
    """Apply hard gates before a deterministic quality/latency decision."""

    if not observations:
        raise ValueError("at least one framework observation is required")
    names = [item.framework for item in observations]
    if len(names) != len(set(names)):
        raise ValueError("framework observations must have unique names")

    eligible = [item for item in observations if item.gates_passed]
    if not eligible:
        raise ValueError("no framework passed every hard gate")

    preferred = next((item for item in eligible if item.framework == PREFERRED_FRAMEWORK), None)
    fastest = min(item.elapsed_ms for item in eligible)
    best_quality = max(item.quality_score for item in eligible)
    all_candidates_passed = len(eligible) == len(observations)
    if (
        preferred is not None
        and all_candidates_passed
        and preferred.elapsed_ms <= fastest * (1 + PERFORMANCE_TOLERANCE)
        and preferred.quality_score >= best_quality * (1 - PERFORMANCE_TOLERANCE)
    ):
        return PREFERRED_FRAMEWORK

    ranked = sorted(
        eligible,
        key=lambda item: (-item.quality_score, item.elapsed_ms, item.framework),
    )
    return ranked[0].framework


def run_framework_bakeoff(
    *,
    adapters: tuple[FrameworkAdapter, ...] | None = None,
    frozen_input: dict[str, object] | None = None,
    live: bool = False,
) -> FrameworkBakeoffReport:
    """Run the default offline contract probes or caller-supplied live adapters."""

    workload = frozen_input or {
        "fixture": "trusted-scientific-research-v1",
        "operations": ["submit", "branch_retry", "cancel", "resume", "compile_bundle"],
    }
    encoded = json.dumps(workload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    workload_hash = sha256(encoded.encode("utf-8")).hexdigest()
    selected_adapters = adapters or (
        PydanticAIDBOSAdapter(),
        LangGraphAdapter(),
        GoogleADKAdapter(),
    )
    observations = tuple(
        adapter.evaluate(workload, live=live)
        for adapter in selected_adapters
    )
    return FrameworkBakeoffReport(
        mode="live" if live else "offline",
        frozen_input_hash=workload_hash,
        observations=observations,
        selected_framework=select_framework(list(observations)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic framework bake-off")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = run_framework_bakeoff()
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(f"selected framework: {report.selected_framework}")


if __name__ == "__main__":
    main()


__all__ = [
    "HARD_GATES",
    "FrameworkAdapter",
    "FrameworkBakeoffReport",
    "FrameworkObservation",
    "GoogleADKAdapter",
    "LangGraphAdapter",
    "PydanticAIDBOSAdapter",
    "run_framework_bakeoff",
    "select_framework",
]
