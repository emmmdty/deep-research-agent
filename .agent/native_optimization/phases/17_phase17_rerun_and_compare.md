# Phase 17 — Rerun, compare, and regenerate artifacts

## Objective
Rerun the affected native benchmark surfaces and generate explicit before/after comparison artifacts.

## Required outcomes
Create:
- `evals/reports/native_optimization/optimization_summary.json`
- `evals/reports/native_optimization/BEFORE_AFTER.md`

Update as needed:
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`

## Comparison rules
The comparison must include:
- baseline commit and tag
- post-change commit
- selected target
- baseline values
- post-change values
- metric deltas
- whether the result is positive, negative, or inconclusive
- notes on any regression or tradeoff

## Acceptance
This phase passes only when:
- smoke_local still passes
- the affected regression_local suite(s) rerun successfully
- comparison artifacts are machine-readable and human-readable
- all artifact paths are repo-relative
- the comparison is honest about regressions or inconclusive outcomes

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --variant smoke_local --output-root /tmp/native_opt_validation/company12_smoke --json`
- rerun the affected regression_local suite(s)
- rebuild any native summaries/scorecards needed for the selected target
