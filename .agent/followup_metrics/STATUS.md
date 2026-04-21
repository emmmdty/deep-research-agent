# Follow-up Metrics Run Status

## Static run info
- run_id: followup-metrics-20260421T151225Z
- main_repo_abs: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_branch: main
- worktrees_root: ../_codex_worktrees
- started_at: 2026-04-21T15:12:25Z
- codex_model: gpt-5.4
- codex_reasoning_effort: medium
- sandbox_mode: danger-full-access
- approval_policy: never

## Baseline import
- final_baseline_commit: 791c44b982110e115731a62b119306f0093accf4
- baseline_release_manifest_path: evals/reports/phase5_local_smoke/release_manifest.json
- baseline_release_gate_status: passed
- baseline_headline_metrics_imported: yes

## Command registry additions
- metric_runner: UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --output-root evals/reports/followup_metrics --json
- ablation_runner:
- scorecard_renderer:
- latency_profiler:
- cost_aggregator:

## Current overall status
- current_phase: phase8_ablation_and_perf
- current_phase_slug: phase8-ablation-and-perf
- current_attempt: 0
- last_successful_phase: phase7_metrics_instrumentation
- overall_state: in_progress

## Worktree state
- active_branch: main
- active_worktree: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_clean_before_phase: yes
- post_merge_smoke_status:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_cli_runtime.py tests/test_phase7_value_metrics.py` -> pass (18 passed)
  - temp-root fresh measured rerun (`main.py eval run --suite company12 --output-root /tmp/main-phase7-company12 --capture-runtime-metrics --json`) -> pass
  - temp-root value-metrics render (`scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --source-root /tmp/main-phase7-company12 --output-root /tmp/main-phase7-metrics --json`) -> pass

## Local-only / ignored asset audit
- checked_paths: .env, .env.*, .venv, .codex/config.toml, .python-version, workspace/, venv_gptr/
- missing_assets: none
- recreated_assets:
- symlinked_assets: .env, .venv, .codex/config.toml, workspace/, venv_gptr/
- copied_assets: .agent/followup_metrics/ seeded from /tmp/followup_metrics_seed after backing up the untracked main-worktree copy
- blockers_from_local_assets: none

## Phase ledger

### Phase 7 - metrics_instrumentation
- status: completed
- attempts: 1
- summary: Added the canonical Phase 7 value-metrics module and script, introduced an opt-in runtime-measurement sidecar for fresh eval reruns, generated the follow-up metrics artifacts under `evals/reports/followup_metrics/`, and tracked the follow-up control docs under their canonical filenames.
- acceptance_checks:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_cli_runtime.py tests/test_phase7_value_metrics.py` -> pass (18 passed)
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --output-root evals/reports/followup_metrics --json` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root evals/reports/followup_metrics/company12_fresh --capture-runtime-metrics --json` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --source-root evals/reports/followup_metrics/company12_fresh --output-root evals/reports/followup_metrics --json` -> pass
- artifacts:
- `.agent/followup_metrics/METRICS_SPEC.md`
- `.agent/followup_metrics/STATUS.md`
- `docs/final/METRIC_DEFINITIONS.md`
- `scripts/run_value_metrics.py`
- `src/deep_research_agent/evals/value_metrics.py`
- `evals/reports/followup_metrics/headline_metrics.json`
- `evals/reports/followup_metrics/value_dashboard.json`
- `evals/reports/followup_metrics/stage_timing_breakdown.json`
- `evals/reports/followup_metrics/company12_fresh/company-openai-surface/runtime_metrics.json`
- `tests/test_phase7_value_metrics.py`
- blockers:
- notes:
  - main baseline verified before worktree creation: `uv run python main.py --help` -> pass, temp-root local release smoke -> pass, broad Phase 6 regression slice -> pass (98 passed)
  - renamed `.agent/followup_metrics/METRICE_SPEC.md` to the canonical `METRICS_SPEC.md`
  - committed Phase 5 smoke artifacts still yield `null` timing metrics with reason `frozen_artifact_timestamps`; the fresh measured `company12` rerun upgrades `ttff_seconds_p50=0.299367` and `ttfr_seconds_p50=1.344091`
  - merged to `main` via commit `bf200d264779486a00a2602f391ac3aa2ce40b8b` and cleared the Phase 7 mainline smoke on the merged tree
  - worktree-local bootstrap symlinks remain untracked and will be removed before cleanup

### Phase 8 - ablation_and_perf
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 9 - value_pack
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

## Headline metrics snapshot
- completion_rate: 1.0
- bundle_emission_rate: 1.0
- critical_claim_support_precision: 1.0
- citation_error_rate: 0.0
- provenance_completeness: 1.0
- policy_compliance_rate: 1.0
- resume_success_rate: 1.0
- stale_recovery_success_rate: 1.0
- file_input_success_rate: 1.0
- conflict_detection_recall: 1.0
- ttff_seconds_p50: 0.299367
- ttfr_seconds_p50: 1.344091
- estimated_api_cost_per_completed_job: null (`provider_free_fixture_run`)

## Ablation deltas snapshot
- audit_value_delta:
- source_policy_value_delta:
- evidence_first_value_delta:
- rerank_value_delta:
- provider_routing_value_delta:
- new_runtime_value_delta:

## Decisions log
- [2026-04-21T15:12:25Z] Follow-up metrics run started from `main@791c44b982110e115731a62b119306f0093accf4`.
- [2026-04-21T15:12:25Z] Backed up the untracked `.agent/followup_metrics/` tree to `/tmp/followup_metrics_seed` before removing it from the main worktree to avoid merge conflicts when Phase 7 starts tracking those paths.
- [2026-04-21T15:12:25Z] Verified previous accepted baseline on `main`: CLI help pass, temp-root local release smoke pass, broad Phase 6 regression slice pass (98 passed).
- [2026-04-21T15:12:25Z] Created worktree `../_codex_worktrees/phase7-metrics-instrumentation-attempt-1` on branch `codex/phase7-metrics-instrumentation/attempt-1`.
- [2026-04-21T15:12:25Z] Bootstrapped local-only assets via symlinks for `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`.
- [2026-04-21T15:12:25Z] Phase 7 TDD red step completed: `tests/test_phase7_value_metrics.py` failed first with missing `run_value_metrics` support and missing `capture_runtime_metrics`.
- [2026-04-21T15:12:25Z] Phase 7 green step completed: implemented `src/deep_research_agent/evals/value_metrics.py`, `scripts/run_value_metrics.py`, the fresh rerun runtime sidecar, and `docs/final/METRIC_DEFINITIONS.md`.
- [2026-04-21T15:12:25Z] Phase 7 acceptance passed in the worktree and produced `headline_metrics.json`, `value_dashboard.json`, `stage_timing_breakdown.json`, and a fresh measured `company12` runtime sidecar under `evals/reports/followup_metrics/`.
- [2026-04-21T15:12:25Z] Merged Phase 7 into `main` via `bf200d264779486a00a2602f391ac3aa2ce40b8b` and reran the Phase 7 mainline smoke successfully.
