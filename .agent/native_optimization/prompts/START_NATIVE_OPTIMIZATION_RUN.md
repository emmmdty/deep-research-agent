Treat AGENTS.md as the controlling instruction layer.

This repository has already completed:
- architecture migration
- follow-up metrics/value-pack
- benchmark portfolio integration
- native regression benchmark expansion

Do NOT restart earlier phases.
This run has exactly 3 self-driven tasks:
1. freeze the current native regression baseline by creating the local annotated tag `v0.2.0-native-regression`
2. run one native benchmark optimization cycle based on regression_local results
3. write a simplified Chinese usage manual for the native benchmark system

Read these files in order before making changes:
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
18. .agent/native_optimization/IMPLEMENT.md
19. .agent/native_optimization/STATUS.md
20. .agent/native_optimization/phases/15_phase15_freeze_and_select.md
21. .agent/native_optimization/phases/16_phase16_optimize_weakest_native_axis.md
22. .agent/native_optimization/phases/17_phase17_rerun_and_compare.md
23. .agent/native_optimization/phases/18_phase18_manual_and_handoff.md

Run only phases 15–18.
Do not work on external benchmarks.
Do not implement provider-backed full native runs.
Do not require OpenAI or Anthropic secrets in this run.

Mandatory loop for each phase:
- verify the previous accepted baseline on main
- create a fresh linked git worktree and branch
- bootstrap the worktree if ignored/local-only assets are needed
- execute only the current phase scope
- run phase acceptance checks
- if pass: commit, merge into main, rerun required main smoke, remove worktree, delete branch, update `.agent/native_optimization/STATUS.md`, continue
- if fail: stay in the same worktree, revise the current phase file with failure analysis and a revised plan, update STATUS, repair, retry
- maximum 4 attempts per phase
- if any phase fails 4 times, stop and report blockers precisely

Critical rules:
- create the local annotated tag `v0.2.0-native-regression` before optimization work begins
- if the tag already exists, inspect it and do not force-move it silently
- choose exactly one optimization target using the rules in Phase 15
- if all metrics are saturated, optimize benchmark discriminativeness or reviewer-facing clarity rather than inventing a fake weakness
- keep smoke_local as the authoritative release gate
- keep diffs narrowly scoped to the selected target and the required handoff docs
- do not fabricate gains
- if the optimization is inconclusive, record that honestly in the comparison artifact

Required end-state deliverables:
- local annotated tag `v0.2.0-native-regression`
- `evals/reports/native_optimization/optimization_summary.json`
- `evals/reports/native_optimization/BEFORE_AFTER.md`
- `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`
- `docs/final/NATIVE_OPTIMIZATION_REPORT.md`
- updated native scorecard/casebook/summaries if affected

Print continuously:
- current phase
- why you are doing it now
- selected target and rationale
- files changed
- commands run
- pass/fail outcomes
- remaining work

Start now with Phase 15.
