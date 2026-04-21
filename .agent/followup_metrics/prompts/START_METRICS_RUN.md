Treat AGENTS.md as the controlling instruction layer.

This is a follow-up execution run.
Do not rerun the old Phase 0–6 architecture migration.
Use the current `main` branch and the committed release artifacts as the baseline.

Read these files in order before making changes:
1. AGENTS.md
2. .agent/context/PROJECT_SPEC.md
3. .agent/context/TASK2_SPEC.yaml
4. .agent/PREFLIGHT_DOC_AUDIT.md
5. .agent/STATUS.md
6. FINAL_CHANGE_REPORT.md
7. docs/final/EXPERIMENT_SUMMARY.md
8. evals/reports/phase5_local_smoke/release_manifest.json
9. .agent/followup_metrics/METRICS_SPEC.md
10. .agent/followup_metrics/PHASE_PLAN.md
11. .agent/followup_metrics/IMPLEMENT.md
12. .agent/followup_metrics/STATUS.md
13. .agent/followup_metrics/phases/07_phase7_metrics_instrumentation.md
14. .agent/followup_metrics/phases/08_phase8_ablation_and_perf.md
15. .agent/followup_metrics/phases/09_phase9_value_pack.md

Run only follow-up phases 7–9.

Mandatory loop for every follow-up phase:
- verify the previous accepted baseline on main
- create a fresh linked git worktree and branch
- bootstrap the worktree, explicitly checking ignored/local-only assets
- execute only the current phase scope
- run the phase acceptance checks
- if acceptance passes, commit, merge into main, rerun required main smoke, remove the worktree, delete the branch, update .agent/followup_metrics/STATUS.md, and continue
- if acceptance fails, stay in the same phase worktree, revise the current phase file with failure analysis and a revised plan, update .agent/followup_metrics/STATUS.md, repair the phase, and retry
- maximum 4 attempts per phase
- if any phase fails 4 times, stop the entire run, keep the failing worktree intact, and report the current phase, blockers, failed validations, and the exact next manual action

Important requirements:
- do not ask for routine confirmation
- keep diffs scoped to the active phase
- continuously update .agent/followup_metrics/STATUS.md
- print what you are doing, why, commands run, files changed, and outcomes
- do not fabricate metrics, costs, or ablation gains
- if a metric cannot be computed, output null plus reason
- if an ablation is not comparable, mark it explicitly and explain why
- the final result must leave the repository with a clear value scorecard that proves what this Deep Research Agent does

Start now with Phase 7.