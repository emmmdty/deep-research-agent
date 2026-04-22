# Phase 7 — Native Regression Expansion

## Objective
Expand the native/custom benchmark layer from smoke-only into a real deterministic regression tier while preserving `phase5_local_smoke` as the authoritative merge-safe release gate.

## Required outcomes
- preserve the existing `smoke_local` suite behavior and committed `phase5_local_smoke` manifest contract
- add `regression_local` variants for `company12`, `industry12`, `trusted8`, `file8`, and `recovery6`
- reach exact task counts: `12 / 12 / 8 / 8 / 6`
- keep all regression inputs deterministic, repo-local, and reproducible
- add a reviewer-facing native benchmark reporting layer and committed regression artifacts

## Must produce
- variant-aware native eval runner and CLI contract
- expanded deterministic datasets, fixtures, and rubrics for the five suite families
- `scripts/run_native_regression.py`
- `scripts/build_native_benchmark_summary.py`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`
- `docs/benchmarks/native/README.md`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`

## Constraints
- do not remove or weaken the current `smoke_local` release-smoke path
- do not invent fake task counts or silently shrink targets
- do not add live web dependence to `regression_local`
- do not require OpenAI/Anthropic secrets or provider-backed full-native runs
- keep benchmark logic under `evals/`, `scripts/`, `configs/`, `docs/`, `tests/`, and canonical eval modules

## Acceptance
This phase passes only when:
- `smoke_local` remains runnable and green
- all five suites support `regression_local`
- exact target task counts are met
- native regression outputs are deterministic and repo-relative
- required regression reports and docs exist and point to real artifacts
- focused tests and lint pass
- final `git status --short` is clean after committed artifact regeneration

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused native benchmark tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --variant smoke_local --output-root /tmp/native_regression_validation/company12_smoke --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --variant regression_local --output-root /tmp/native_regression_validation/company12_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite industry12 --variant regression_local --output-root /tmp/native_regression_validation/industry12_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite trusted8 --variant regression_local --output-root /tmp/native_regression_validation/trusted8_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite file8 --variant regression_local --output-root /tmp/native_regression_validation/file8_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --variant regression_local --output-root /tmp/native_regression_validation/recovery6_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json`
- `git status --short`

## Implementation notes
- keep suite names unchanged; add a `variant` dimension with default `smoke_local`
- preserve current smoke datasets and committed `phase5_local_smoke` outputs byte-for-byte unless validation proves a repair is required
- generate native scorecard/casebook from real suite summaries and task artifacts rather than from hand-written examples
- current scope is AI-ecosystem-focused native cases, consistent with the repository’s existing research narrative
