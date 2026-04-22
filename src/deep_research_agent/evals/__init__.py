"""Canonical Phase 05 evaluation surfaces."""

from __future__ import annotations

from .contracts import EVAL_SUITE_NAMES, EVAL_VARIANT_NAMES
from .external import BENCHMARK_NAMES, run_external_benchmark
from .native_benchmark import build_native_benchmark_summary, run_native_regression
from .runner import run_eval_suite

__all__ = [
    "BENCHMARK_NAMES",
    "EVAL_SUITE_NAMES",
    "EVAL_VARIANT_NAMES",
    "build_native_benchmark_summary",
    "run_eval_suite",
    "run_external_benchmark",
    "run_native_regression",
]
