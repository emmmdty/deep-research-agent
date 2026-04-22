Treat AGENTS.md as the base control layer.

This is a benchmark-integration preflight audit only.
Do not start implementation phases in this run.

Read these files in order:
1. AGENTS.md
2. .agent/benchmark_portfolio/AGENTS_OVERLAY.md
3. .agent/context/PROJECT_SPEC.md
4. .agent/context/TASK2_SPEC.yaml
5. .agent/PREFLIGHT_DOC_AUDIT.md
6. .agent/STATUS.md
7. FINAL_CHANGE_REPORT.md
8. docs/final/EXPERIMENT_SUMMARY.md
9. docs/final/VALUE_SCORECARD.md
10. evals/reports/phase5_local_smoke/release_manifest.json
11. .agent/benchmark_portfolio/BENCHMARK_SPEC.md
12. .agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml
13. .agent/benchmark_portfolio/PHASE_PLAN.md
14. .agent/benchmark_portfolio/IMPLEMENT.md
15. .agent/benchmark_portfolio/STATUS.md
16. all files under .agent/benchmark_portfolio/phases/

Your task:
- verify all benchmark_portfolio control docs exist
- verify BENCHMARK_PLAN_SPEC.yaml parses
- verify the current repo baseline still matches the benchmark spec assumptions
- verify the current repo still has native eval/release assets
- identify any conflicts between the existing AGENTS.md / .agent docs and this benchmark_portfolio runbook
- write `.agent/benchmark_portfolio/PREFLIGHT_BENCHMARK_AUDIT.md`
- update `.agent/benchmark_portfolio/STATUS.md`

Output verdict must be exactly one of:
- READY
- READY_WITH_MINOR_DOC_FIXES
- NOT_READY

Do not create worktrees in this preflight run.
Do not implement benchmark adapters yet.
Stop after the benchmark control-layer preflight is complete.
