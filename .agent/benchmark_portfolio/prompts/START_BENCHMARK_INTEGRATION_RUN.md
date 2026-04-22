Treat AGENTS.md as the base control layer.
Then treat `.agent/benchmark_portfolio/AGENTS_OVERLAY.md` as the task-specific control layer for this run.

This repo has already completed the main architecture migration and the follow-up metrics/value-pack run.
Do not restart the old migration phases.
Run only benchmark integration phases 10–14.

Read in order:
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
16. .agent/benchmark_portfolio/phases/10_phase10_scaffolding_and_facts.md
17. .agent/benchmark_portfolio/phases/11_phase11_longfact_safe.md
18. .agent/benchmark_portfolio/phases/12_phase12_longbench_v2.md
19. .agent/benchmark_portfolio/phases/13_phase13_browsecomp_and_gaia.md
20. .agent/benchmark_portfolio/phases/14_phase14_portfolio_docs_and_gate.md

Use the current `main` branch as accepted baseline.
Execute only benchmark integration phases 10–14.

Mandatory loop for every phase:
- verify previous accepted baseline on main
- create a fresh linked git worktree and branch
- bootstrap the worktree, explicitly checking ignored/local-only assets
- complete only the current phase scope
- run the phase acceptance checks
- if acceptance passes, commit, merge into main, rerun required main smoke, remove worktree, delete branch, update `.agent/benchmark_portfolio/STATUS.md`, and continue
- if acceptance fails, stay in the same phase worktree, revise the current phase file with failure analysis and a revised plan, update STATUS, repair, retry
- maximum 4 attempts per phase
- if any phase fails 4 times, stop and report blockers precisely

Critical benchmark-specific rules:
- keep custom native benchmark as the authoritative release gate
- do not let external benchmarks replace the current release smoke gate
- BrowseComp must have integrity guard and remain challenge-only
- GAIA must be capability-gated and subset-first
- FACTS Grounding is the first external regression priority
- LongBench v2 must be bucketed by context length
- do not fabricate external benchmark scores
- if a benchmark cannot run because of access, capability, or cost, build the harness, save a blocked report, and continue with the rest

Print continuously:
- what phase you are in
- why you are doing it now
- what files you changed
- what commands you ran
- what passed or failed
- what remains

Start now with Phase 10.
