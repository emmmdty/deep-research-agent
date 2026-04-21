# Evals

Canonical evaluation assets for the deterministic deep research runtime.

This tree is the Phase 5 source of truth for:

- suite definitions under `evals/suites/`
- frozen low-cost datasets under `evals/datasets/`
- rubric metadata under `evals/rubrics/`
- committed local smoke outputs under `evals/reports/`
- migration notes for legacy benchmark tooling under `evals/legacy_diagnostics/`

The runnable local entrypoints are:

- `uv run python main.py eval run --suite company12`
- `uv run python main.py eval run --suite industry12`
- `uv run python main.py eval run --suite trusted8`
- `uv run python main.py eval run --suite file8`
- `uv run python main.py eval run --suite recovery6`
- `uv run python scripts/run_local_release_smoke.py`
