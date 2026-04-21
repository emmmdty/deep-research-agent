"""Public gateway surfaces for CLI, API, and batch entrypoints."""

from __future__ import annotations

from .cli import build_parser, main, run_cli, run_command

__all__ = ["build_parser", "main", "run_cli", "run_command"]
