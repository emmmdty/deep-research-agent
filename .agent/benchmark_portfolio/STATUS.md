# Benchmark Portfolio Run Status

## Static run info
- run_id: benchmark-preflight-20260422T073343Z
- main_repo_abs: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_branch: main
- worktrees_root: ../_codex_worktrees
- started_at: 2026-04-22T07:33:43Z
- codex_model: gpt-5.4
- codex_reasoning_effort: medium
- sandbox_mode: workspace-write
- approval_policy: auto_review

## Baseline import
- baseline_commit: a4f31ddb16a78035d983c54e0a86c4d713d71619
- baseline_release_manifest: evals/reports/phase5_local_smoke/release_manifest.json
- baseline_value_scorecard: docs/final/VALUE_SCORECARD.md
- benchmark_portfolio_run_started_from_clean_main: no

## Command registry additions
- benchmark_runner: not added in preflight
- portfolio_summary_builder: not added in preflight
- facts_runner: not added in preflight
- longfact_safe_runner: not added in preflight
- longbench_runner: not added in preflight
- browsecomp_runner: not added in preflight
- gaia_runner: not added in preflight

## Current overall status
- current_phase: preflight
- current_phase_slug: preflight-benchmark-audit
- current_attempt: 1
- last_successful_phase: none
- overall_state: not_ready

## Worktree state
- active_branch: main
- active_worktree: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_clean_before_phase: no
- post_merge_smoke_status: not applicable; no benchmark phase was merged in this preflight run

## Local-only / ignored asset audit
- checked_paths: .env, .venv, .python-version, workspace/, .codex/, provider keys / benchmark cache / gated dataset cache
- missing_assets: not audited in a worktree because preflight did not create one
- recreated_assets:
- symlinked_assets:
- copied_assets:
- blockers_from_local_assets: none found in this control-layer preflight; the hard blocker is that .agent/benchmark_portfolio/* is untracked on main

## Phase ledger

### Phase 10 - scaffolding_and_facts
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 11 - longfact_safe
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 12 - longbench_v2
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 13 - browsecomp_and_gaia
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 14 - portfolio_docs_and_gate
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

## Portfolio snapshot
- current_authoritative_gate: native Phase 5 local smoke suites (company12, industry12, trusted8, file8, recovery6)
- current_secondary_regression: facts_grounding planned but not implemented
- current_challenge_tracks: browsecomp_guarded, gaia_supported_subset, and longbench_v2 medium/long are planned only
- implemented_adapters: none in benchmark_portfolio preflight
- deferred_adapters: facts_grounding, longfact_safe, longbench_v2, browsecomp, gaia
- open_integrity_risks: untracked benchmark control layer on main; legacy benchmark/comparator diagnostics must stay distinct from the new external benchmark substrate

## Decisions log
- [2026-04-22T07:33:43Z] Started benchmark portfolio control-layer preflight only; no worktree created and no benchmark phase started.
- [2026-04-22T07:33:43Z] Verified that all requested benchmark control docs exist locally under .agent/benchmark_portfolio/.
- [2026-04-22T07:33:43Z] Parsed .agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml successfully.
- [2026-04-22T07:33:43Z] Verified the native baseline artifacts still exist: main.py eval surface, Phase 5 release manifest, follow-up metrics, and native suite definitions.
- [2026-04-22T07:33:43Z] Detected that .agent/benchmark_portfolio/ is untracked on main (git status shows ?? .agent/benchmark_portfolio/; git ls-files returns no tracked files).
- [2026-04-22T07:33:43Z] Recorded preflight verdict: NOT_READY.
