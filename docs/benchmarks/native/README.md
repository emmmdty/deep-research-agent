# Native Benchmark

This directory contains the reviewer-facing documentation for the repo-native benchmark surface.

Authoritative baseline:

- `smoke_local` remains the authoritative merge-safe gate under `evals/reports/phase5_local_smoke/`.
- `regression_local` expands deterministic native coverage under `evals/reports/native_regression/`.

Key review artifacts:

- `NATIVE_SCORECARD.md`
- `CASEBOOK.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`

Rebuild commands:

- `uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json`
- `uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json`

This layer stays deterministic and repo-local. It does not require provider secrets or external benchmark integration.
