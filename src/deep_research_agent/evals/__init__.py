"""Canonical Phase 05 evaluation surfaces."""

from __future__ import annotations

from .contracts import EVAL_SUITE_NAMES
from .external import BENCHMARK_NAMES, run_external_benchmark
from .runner import run_eval_suite

__all__ = ["BENCHMARK_NAMES", "EVAL_SUITE_NAMES", "run_eval_suite", "run_external_benchmark"]
