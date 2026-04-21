"""Thin wrapper that delegates the public CLI entrypoint to the src package."""

from __future__ import annotations

import sys

# The canonical CLI implementation now lives in `deep_research_agent.gateway.cli`.
from deep_research_agent.gateway import cli as _cli

get_settings = _cli.get_settings
_build_job_service = _cli._build_job_service


def build_parser():
    original_get_settings = _cli.get_settings
    _cli.get_settings = get_settings
    try:
        return _cli.build_parser()
    finally:
        _cli.get_settings = original_get_settings


def run_cli(*args, **kwargs):
    original_get_settings = _cli.get_settings
    _cli.get_settings = get_settings
    try:
        return _cli.run_cli(*args, **kwargs)
    finally:
        _cli.get_settings = original_get_settings


def run_command(argv=None):
    original_get_settings = _cli.get_settings
    original_build_job_service = _cli._build_job_service
    _cli.get_settings = get_settings
    _cli._build_job_service = _build_job_service
    try:
        return _cli.run_command(argv)
    finally:
        _cli.get_settings = original_get_settings
        _cli._build_job_service = original_build_job_service


def main():
    raise SystemExit(run_command(sys.argv[1:]))

__all__ = ["_build_job_service", "build_parser", "get_settings", "main", "run_cli", "run_command"]


if __name__ == "__main__":
    main()
