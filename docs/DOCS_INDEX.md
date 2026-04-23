# Documentation Index

This is the recommended reading order for reviewers.

## Fast Path

1. [`README.md`](../README.md) - project purpose, public surfaces, quickstart, and current limits.
2. [`REPO_MAP.md`](./REPO_MAP.md) - where canonical code, docs, evals, compatibility shims, and legacy material live.
3. [`FINAL_CHANGE_REPORT.md`](../FINAL_CHANGE_REPORT.md) - final architecture migration summary.
4. [`docs/final/EXPERIMENT_SUMMARY.md`](./final/EXPERIMENT_SUMMARY.md) - release smoke, native regression, external portfolio, and follow-up metrics summary.
5. [`docs/final/VALUE_SCORECARD.md`](./final/VALUE_SCORECARD.md) - measured value pack.
6. [`docs/benchmarks/native/README.md`](./benchmarks/native/README.md) - native benchmark overview.
7. [`docs/benchmarks/native/NATIVE_SCORECARD.md`](./benchmarks/native/NATIVE_SCORECARD.md) - smoke and regression scorecard.
8. [`docs/benchmarks/native/CASEBOOK.md`](./benchmarks/native/CASEBOOK.md) - selected deterministic regression cases.
9. [`docs/final/NATIVE_OPTIMIZATION_REPORT.md`](./final/NATIVE_OPTIMIZATION_REPORT.md) - latest native benchmark hardening cycle.

## Engineering Detail

- [`docs/architecture.md`](./architecture.md) - implemented architecture and current limits.
- [`docs/development.md`](./development.md) - local commands, validation, and compatibility notes.
- [`specs/api-readiness-contract.md`](../specs/api-readiness-contract.md) - implemented local HTTP API and batch contract.
- [`docs/adr/adr-0008-http-api-surface.md`](./adr/adr-0008-http-api-surface.md) - local HTTP API decision.
- [`docs/adr/adr-0009-batch-and-artifact-contract.md`](./adr/adr-0009-batch-and-artifact-contract.md) - batch and artifact contract decision.
- [`docs/migration/TREE_HYGIENE.md`](./migration/TREE_HYGIENE.md) - repository tree hygiene record.

## Benchmark Evidence

- [`evals/reports/phase5_local_smoke/release_manifest.json`](../evals/reports/phase5_local_smoke/release_manifest.json) - authoritative merge-safe gate.
- [`evals/reports/native_regression/native_summary.json`](../evals/reports/native_regression/native_summary.json) - deterministic native regression summary.
- [`evals/reports/native_optimization/BEFORE_AFTER.md`](../evals/reports/native_optimization/BEFORE_AFTER.md) - latest before/after benchmark-hardening summary.
- [`docs/benchmarks/README.md`](./benchmarks/README.md) - layered native and external benchmark docs.
- [`docs/benchmarks/PORTFOLIO.md`](./benchmarks/PORTFOLIO.md) - external benchmark portfolio boundaries.

## Historical Context

- [`docs/archive/PLANS-legacy-release-train.md`](./archive/PLANS-legacy-release-train.md) - old release-train plan, retained as history.
- [`docs/refactor/README.md`](./refactor/README.md) - earlier refactor notes.
- [`docs/codex/README.md`](./codex/README.md) - old planning templates.
- [`legacy/README.md`](../legacy/README.md) - archive root marker.
