# Phase 15 — Freeze baseline and select optimization target

## Objective
Freeze the current native regression baseline and choose exactly one optimization target using explicit rules.

## Required outcomes
- verify current `main` baseline
- create the local annotated tag `v0.2.0-native-regression`
- read current native regression artifacts
- select exactly one optimization target
- write the target-selection rationale into `.agent/native_optimization/STATUS.md`
- create a compact baseline snapshot for comparison

## Required reading
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`

## Decision rules
Choose the target using this order:
1. any failed threshold
2. lowest groundedness/provenance/rubric/policy metric
3. slowest or most operationally expensive suite if quality is already saturated
4. weakest reviewer-facing reporting/casebook clarity if metrics are saturated
5. benchmark discriminativeness if all metrics and reports are saturated and too easy

## Acceptance
This phase passes only when:
- the baseline tag exists locally and points to the verified baseline commit
- one target and one only is selected
- the selection rationale is explicit and references real observed artifacts/metrics
- a baseline snapshot artifact exists or is embedded in STATUS for Phase 17 comparison

## Validation
Run at least:
- `git status --short`
- `git rev-parse --short HEAD`
- inspect native benchmark artifacts and summaries
- create the annotated tag locally
- confirm the tag with `git show --stat v0.2.0-native-regression --no-patch`
