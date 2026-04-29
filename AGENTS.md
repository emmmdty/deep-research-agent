# Repository Agent Instructions

This is the public automation guide for the Deep Research Agent repository.

## Project Boundary

- `src/deep_research_agent/` is the canonical Python implementation.
- `main.py` is a thin CLI wrapper around `deep_research_agent.gateway.cli`.
- Root packages such as `artifacts/`, `connectors/`, `services/`, `policies/`, `tools/`, and `evaluation/` are compatibility or diagnostic surfaces unless `docs/REPO_MAP.md` says otherwise.
- Do not make the legacy multi-agent graph the product story.

## Local Workflow

- Use Ubuntu/WSL-friendly shell commands.
- Prefer `uv` for Python work: `uv sync`, `uv run`, and project-local commands from `pyproject.toml`.
- Do not install packages into system Python.
- Do not run GPU training or GPU inference locally.

## Required Smoke Checks

Run these for repository-surface changes:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
```

For broader runtime changes, also run the focused runtime regressions:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/test_phase2_jobs.py \
  tests/test_phase3_connectors.py \
  tests/test_phase4_auditor.py \
  tests/test_phase4_surfaces.py \
  tests/test_cli_runtime.py
```

## Editing Rules

- Keep diffs scoped to the requested behavior.
- Preserve `pyproject.toml` `src` layout and package discovery.
- Do not delete code still imported by the current runtime or covered compatibility tests.
- Archive or remove old local planning records from the public GitHub surface; keep reviewer-facing docs concise.
