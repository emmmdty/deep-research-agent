# Native Optimization Runbook

## Purpose
This runbook governs the next self-driven Codex run after the native regression benchmark expansion.

## Source of truth
Read and follow these in order:
1. AGENTS.md
2. .agent/context/PROJECT_SPEC.md
3. .agent/context/TASK2_SPEC.yaml
4. .agent/STATUS.md
5. FINAL_CHANGE_REPORT.md
6. docs/final/EXPERIMENT_SUMMARY.md
7. evals/reports/phase5_local_smoke/release_manifest.json
8. .agent/native_benchmark/PREFLIGHT_NATIVE_BENCHMARK_AUDIT.md
9. .agent/native_benchmark/STATUS.md
10. docs/benchmarks/native/README.md
11. docs/benchmarks/native/NATIVE_SCORECARD.md
12. docs/benchmarks/native/CASEBOOK.md
13. evals/reports/native_regression/release_manifest.json
14. evals/reports/native_regression/native_summary.json
15. evals/reports/native_regression/RESULTS.md
16. .agent/native_optimization/OPTIMIZATION_SPEC.md
17. .agent/native_optimization/PHASE_PLAN.md
18. .agent/native_optimization/STATUS.md
19. active file under .agent/native_optimization/phases/

## Operating rules
- Do not restart older architecture or benchmark integration phases.
- Do not touch external benchmark code or docs in this run unless the selected optimization target requires a tiny compatibility note.
- Keep diffs scoped to the selected native optimization target.
- Update `.agent/native_optimization/STATUS.md` continuously.
- If all current metrics are saturated, you must explicitly choose a benchmark discriminativeness/reporting target instead of inventing a fake performance issue.
- Do not fabricate gains.
- If an optimization does not improve the selected dimension, record that honestly in the comparison artifact.

## Worktree protocol
For each phase:
1. verify main baseline
2. create a fresh linked git worktree and branch
3. bootstrap ignored/local-only assets only if needed for the current phase
4. execute only the current phase scope
5. run phase acceptance checks
6. if pass: commit, merge into main, rerun required main smoke, remove worktree, delete branch, continue
7. if fail: stay in the same phase worktree, revise the current phase file, retry
8. maximum 4 attempts per phase
9. if 4 attempts fail, stop and write a blocker report

## Worktree naming
- branch: `codex/phase<NN>-<slug>/attempt-<N>`
- worktree dir: `../_codex_worktrees/phase<NN>-<slug>-attempt-<N>`

## Tagging rules
The tag freeze happens in Phase 15.
Requirements:
- create a local annotated tag named `v0.2.0-native-regression`
- tag the verified baseline commit on main before optimization work begins
- do not force-move the tag if it already exists; instead inspect it and either confirm it matches the intended baseline or stop and record the blocker
- do not push tags to remote in this run unless the environment already permits it and no approval is required; remote push is optional and not required for success

## Required comparison artifacts
At the end of the run, create:
- `evals/reports/native_optimization/optimization_summary.json`
- `evals/reports/native_optimization/BEFORE_AFTER.md`

They must include:
- baseline_commit
- baseline_tag
- selected_target
- rationale
- baseline_metrics
- post_change_metrics
- deltas
- interpretation
- artifact_paths

## Required manual/document output
Create:
- `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`
- `docs/final/NATIVE_OPTIMIZATION_REPORT.md`

The manual must be simplified Chinese and must explain:
- what smoke_local means
- what regression_local means
- what the native benchmark proves
- how to rerun the suites
- how to inspect reports and bundles
- how to interpret key metrics
- what is still not covered

## Stop condition
This run ends only when:
- phases 15–18 are merged into main, or
- one phase reaches 4 failed attempts and a blocker report is written
