# Native Optimization Cycle Spec

## Baseline
The repository has already completed:
- architecture migration
- follow-up metrics/value pack
- benchmark portfolio integration
- native benchmark expansion from smoke_local to regression_local

The current main-branch baseline includes:
- smoke_local native benchmark as the authoritative merge-safe release gate
- regression_local native benchmark variants for:
  - company12
  - industry12
  - trusted8
  - file8
  - recovery6
- reviewer-facing native benchmark artifacts:
  - docs/benchmarks/native/README.md
  - docs/benchmarks/native/NATIVE_SCORECARD.md
  - docs/benchmarks/native/CASEBOOK.md
- machine-readable native regression artifacts:
  - evals/reports/native_regression/release_manifest.json
  - evals/reports/native_regression/native_summary.json
  - evals/reports/native_regression/RESULTS.md

## This run has exactly 3 goals
1. Freeze the current native regression baseline by creating the local annotated git tag `v0.2.0-native-regression`.
2. Use regression_local results to choose exactly one highest-value optimization target and implement a focused improvement cycle.
3. Produce a simplified Chinese user manual that explains how to run, inspect, and interpret the native benchmark system.

## Non-goals
- no external benchmarks
- no provider-backed full native runs
- no new frontend
- no restart of earlier architecture migration phases
- no broad unrelated refactors

## Source of truth for choosing the optimization target
Choose the target by reading and comparing:
- docs/benchmarks/native/NATIVE_SCORECARD.md
- docs/benchmarks/native/CASEBOOK.md
- evals/reports/native_regression/release_manifest.json
- evals/reports/native_regression/native_summary.json
- evals/reports/native_regression/RESULTS.md
- relevant native benchmark tests and fixtures

## Optimization target selection rules
Select exactly one target area using this order:

1. Any failed threshold in regression_local
2. Lowest-quality suite by groundedness / provenance / rubric coverage / policy metrics
3. Highest-latency or most operationally expensive suite if quality is already saturated
4. Weakest reviewer-facing artifact if metrics are saturated and engineering behavior is already stable
5. If all suites are saturated and too easy, treat the problem as benchmark discriminativeness and strengthen the benchmark rather than the runtime

## Allowed optimization target types
- suite data/rubric quality
- evidence/claim/audit quality on the weakest native suite
- file-ingest normalization or provenance on file8
- trusted-only policy/routing enforcement on trusted8
- comparison or synthesis quality on industry12
- company profile/comparison reasoning on company12
- recovery/control-plane stability or clarity on recovery6
- benchmark reporting/casebook clarity if the benchmark is too easy and already saturated

## Disallowed optimization target types for this run
- OpenAI/Anthropic secret-dependent work
- external benchmark adapters
- multi-tenant API/service changes
- broad architectural redesign

## Required outputs by end of run
- local annotated tag: `v0.2.0-native-regression`
- docs/final/NATIVE_OPTIMIZATION_REPORT.md
- docs/benchmarks/native/USAGE_GUIDE.zh-CN.md
- updated native scorecard/casebook/summaries if the optimization affects them
- one machine-readable optimization comparison artifact under:
  - evals/reports/native_optimization/

## Required comparison artifact
At minimum create:
- evals/reports/native_optimization/optimization_summary.json
- evals/reports/native_optimization/BEFORE_AFTER.md

These must show:
- selected optimization target
- baseline metric snapshot
- post-change metric snapshot
- delta
- whether the change helps, hurts, or is inconclusive

## Acceptance target
This run is successful only when:
- the tag exists locally
- one clear optimization target was selected by rule, not by whim
- the optimization was implemented and validated
- before/after comparison artifacts exist
- smoke_local still passes
- relevant regression_local suites rerun and are compared
- docs/benchmarks/native/USAGE_GUIDE.zh-CN.md exists and is reviewer-friendly
