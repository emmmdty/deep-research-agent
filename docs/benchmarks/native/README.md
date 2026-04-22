# Native Benchmark

This directory contains the reviewer-facing documentation for the repo-native benchmark surface.

Authoritative baseline:

- `smoke_local` remains the authoritative merge-safe gate under `evals/reports/phase5_local_smoke/`.
- `regression_local` expands deterministic native coverage under `evals/reports/native_regression/`.

Key review artifacts:

- `NATIVE_SCORECARD.md`
- `CASEBOOK.md`
- `USAGE_GUIDE.zh-CN.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_optimization/optimization_summary.json`
- `docs/final/NATIVE_OPTIMIZATION_REPORT.md`

Rebuild commands:

- `uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json`
- `uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json`
- `uv run python scripts/build_native_optimization_summary.py --baseline-tag v0.2.0-native-regression --reports-root evals/reports/native_regression --output-root evals/reports/native_optimization --json`

This layer stays deterministic and repo-local. It does not require provider secrets or external benchmark integration.
