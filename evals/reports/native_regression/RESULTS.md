# Native Regression Benchmark

- status: `passed`
- smoke_local remains the authoritative merge-safe gate.
- regression_local expands reviewer-facing native coverage but does not replace the release smoke gate.

## Suites

- company12: `passed` (smoke_local=1, regression_local=12)
- industry12: `passed` (smoke_local=1, regression_local=12)
- trusted8: `passed` (smoke_local=1, regression_local=8)
- file8: `passed` (smoke_local=1, regression_local=8)
- recovery6: `passed` (smoke_local=6, regression_local=6)

## Gate Interpretation

- authoritative merge-safe gate: `evals/reports/phase5_local_smoke/release_manifest.json`
- regression manifest: `evals/reports/native_regression/release_manifest.json`
