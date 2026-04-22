"""Shared external benchmark evaluation surface."""

from __future__ import annotations

from .contracts import BENCHMARK_NAMES
from .runner import run_external_benchmark
from .summary import build_benchmark_portfolio_summary

__all__ = ["BENCHMARK_NAMES", "build_benchmark_portfolio_summary", "run_external_benchmark"]
