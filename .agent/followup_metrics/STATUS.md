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
- ablation_runner: UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_ablation_pack.py --baseline-root evals/reports/phase5_local_smoke --followup-root evals/reports/followup_metrics --output-root evals/reports/followup_metrics --json
- scorecard_renderer: UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_value_scorecard.py --release-manifest evals/reports/phase5_local_smoke/release_manifest.json --metrics-root evals/reports/followup_metrics --docs-root docs/final --metrics-readme evals/reports/followup_metrics/README.md --json
- latency_profiler: ablation_runner writes `evals/reports/followup_metrics/latency_cost_summary.json`
- cost_aggregator: ablation_runner imports the committed Phase 7 cost placeholders and records the null-cost reason

## Current overall status
- current_phase: followup_metrics_complete
- current_phase_slug: followup-metrics-complete
- current_attempt: 0
- last_successful_phase: phase9_value_pack
- overall_state: completed

## Worktree state
- active_branch: main
- active_worktree: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_clean_before_phase: yes
- post_merge_smoke_status:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_release_gate.py tests/test_release_runner.py tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py tests/test_phase4_surfaces.py tests/test_phase7_value_metrics.py tests/test_phase8_value_ablations.py tests/test_phase9_value_pack.py` -> pass (81 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass
  - temp-root scorecard render (`scripts/build_value_scorecard.py --release-manifest evals/reports/phase5_local_smoke/release_manifest.json --metrics-root evals/reports/followup_metrics --docs-root /tmp/main-phase9-scorecard-docs --metrics-readme /tmp/main-phase9-followup-metrics-README.md --json`) -> pass
  - `git status --short` after the final rerun -> clean

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
- status: completed
- attempts: 1
- summary: Added the deterministic Phase 8 ablation harness and CLI entrypoint, generated the required ablation/performance pack under `evals/reports/followup_metrics/`, and sanitized provider-routing artifacts so local API keys are never serialized into review outputs.
- acceptance_checks:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_phase7_value_metrics.py tests/test_phase8_value_ablations.py` -> pass (12 passed)
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_ablation_pack.py --baseline-root evals/reports/phase5_local_smoke --followup-root evals/reports/followup_metrics --output-root evals/reports/followup_metrics --json` -> pass
- artifacts:
- `scripts/run_value_ablation_pack.py`
- `src/deep_research_agent/evals/value_ablations.py`
- `tests/test_phase8_value_ablations.py`
- `evals/reports/followup_metrics/ablation_summary.csv`
- `evals/reports/followup_metrics/ablation_summary.md`
- `evals/reports/followup_metrics/latency_cost_summary.json`
- `evals/reports/followup_metrics/provider_routing_comparison.json`
- blockers:
- notes:
- `audit_on_vs_off`: removing support-edge auditing drops `critical_claim_support_precision` from `1.0` to `0.0` and raises unsupported-claim leakage from `0.0` to `1.0` without changing completion.
- `strict_source_policy_vs_relaxed`: relaxing trusted-only enforcement drops `policy_compliance_rate` from `1.0` to `0.667` while completion and bundle emission stay at `1.0`.
- `evidence_first_vs_baseline_synthesis`: clearing snapshot links/support edges drops provenance completeness and support precision from `1.0` to `0.0`, and raises citation error from `0.0` to `1.0`.
- `rerank_on_vs_off`: downgrading one critical support edge reduces `critical_claim_support_precision` from `1.0` to `0.5` with no completion change.
- `provider_auto_vs_manual`: deterministic routing comparison emitted route-plan evidence only; judge auto-route selected `anthropic`, while live latency/cost and quality deltas remain null with reason `no_live_provider_backed_routing_eval`.
- `new_runtime_vs_legacy`: recorded as `not_comparable` with reason `no_like_for_like_legacy_runtime_fixture`.
- Phase 8 initially surfaced a secret-handling regression because the provider routing artifact serialized `api_key` values from local provider profiles; fixed by reducing the artifact to a safe route summary and adding a regression assertion that `api_key` never appears in the JSON.
- merged to `main` via commit `763c153dfc4adf87d5b91b795b541933cef7a311`, passed the required mainline smoke, and the Phase 8 worktree/branch were removed after merge.

### Phase 9 - value_pack
- status: completed
- attempts: 1
- summary: Added a reproducible value-scorecard generator, wrote the committed reviewer-facing scorecard outputs under `docs/final/`, added a follow-up metrics README, and updated the top-level README plus final docs so the project’s measured value is visible without overstating the local-only deployment shape.
- acceptance_checks:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_release_gate.py tests/test_release_runner.py tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py tests/test_phase4_surfaces.py tests/test_phase7_value_metrics.py tests/test_phase8_value_ablations.py tests/test_phase9_value_pack.py` -> pass (81 passed)
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_value_scorecard.py --release-manifest evals/reports/phase5_local_smoke/release_manifest.json --metrics-root evals/reports/followup_metrics --docs-root /tmp/phase9-scorecard-docs --metrics-readme /tmp/phase9-followup-metrics-README.md --json` -> pass
- artifacts:
- `scripts/build_value_scorecard.py`
- `src/deep_research_agent/evals/value_scorecard.py`
- `tests/test_phase9_value_pack.py`
- `docs/final/VALUE_SCORECARD.md`
- `docs/final/VALUE_SCORECARD.json`
- `evals/reports/followup_metrics/README.md`
- `README.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `FINAL_CHANGE_REPORT.md`
- blockers:
- notes:
- Scorecard generation is reproducible from committed artifacts and rewrites public artifact references to repo-relative paths, so the published scorecard no longer depends on deleted worktree paths.
- README now exposes measurable headline values near the top and links directly to the scorecard, experiment summary, and release manifest.
- The value pack preserves the current boundary honestly: the HTTP API is local-only, provider-routing live latency/quality is still unmeasured, and the repo is not positioned as a multi-tenant production SaaS.
- merged to `main` via commit `8f0f5e6e4a772f916918f7d77309d28b5ce0f76d`, passed the final mainline smoke, and the Phase 9 worktree/branch were removed after merge.

## Final follow-up summary
- result: completed
- final_main_commit: `8f0f5e6e4a772f916918f7d77309d28b5ce0f76d`
- release_gate_status: `passed`
- value_scorecard_paths: `docs/final/VALUE_SCORECARD.md`, `docs/final/VALUE_SCORECARD.json`
- measured_headlines: `completion_rate=1.0`, `bundle_emission_rate=1.0`, `critical_claim_support_precision=1.0`, `policy_compliance_rate=1.0`, `resume_success_rate=1.0`, `stale_recovery_success_rate=1.0`, `ttff_seconds_p50=0.299367`, `ttfr_seconds_p50=1.344091`
- strongest_ablation_evidence: audit off causes support precision -1.0 and unsupported-claim leakage +1.0; evidence-first removal causes provenance -1.0 and citation error +1.0; rerank off causes support precision -0.5
- explicit_limits: local-only HTTP API, SQLite/filesystem runtime, no auth or tenant isolation, no live provider cost calculation, provider routing live latency/quality still not measured
- final_repo_state_after_smoke: clean

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
- audit_value_delta: unsupported claim leakage +1.0 and critical claim support precision -1.0 when audit support edges are removed; completion unchanged
- source_policy_value_delta: policy compliance -0.333 when trusted-only enforcement is relaxed; bundle emission and completion unchanged
- evidence_first_value_delta: provenance completeness -1.0, critical claim support precision -1.0, citation error +1.0 without evidence-first grounding
- rerank_value_delta: critical claim support precision -0.5 when rerank-like edge selection is disabled; completion unchanged
- provider_routing_value_delta: deterministic route-plan only; judge auto-route selects `anthropic`, but live latency/quality deltas remain unavailable (`no_live_provider_backed_routing_eval`)
- new_runtime_value_delta: not comparable because no like-for-like legacy runtime fixture remains (`no_like_for_like_legacy_runtime_fixture`)

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
- [2026-04-21T15:12:25Z] Verified the merged Phase 7 baseline on `main@7cb7bfa40c61e5ff2670d8336ac03b3d91c94483`, then created worktree `../_codex_worktrees/phase8-ablation-and-perf-attempt-1` on branch `codex/phase8-ablation-and-perf/attempt-1`.
- [2026-04-21T15:12:25Z] Bootstrapped the Phase 8 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; baseline help check and focused Phase 7 regression test passed in the new worktree.
- [2026-04-21T15:12:25Z] Phase 8 TDD red step completed: `tests/test_phase8_value_ablations.py` failed first because `scripts/run_value_ablation_pack.py` did not exist.
- [2026-04-21T15:12:25Z] Phase 8 green step completed: implemented `src/deep_research_agent/evals/value_ablations.py`, `scripts/run_value_ablation_pack.py`, and the required ablation/performance artifacts under `evals/reports/followup_metrics/`.
- [2026-04-21T15:12:25Z] Phase 8 uncovered a local-secret regression because the initial `provider_routing_comparison.json` serialized provider `api_key` fields from the local settings profile. Replaced raw route dumps with safe summaries and added a regression assertion that `api_key` never appears in the comparison JSON.
- [2026-04-21T15:12:25Z] Phase 8 acceptance passed in the worktree: lint pass, focused regression slice pass (12 passed), ablation pack regenerated, and provider routing output verified as `API_KEY_REDACTED`.
- [2026-04-21T15:12:25Z] Merged Phase 8 into `main` via `763c153dfc4adf87d5b91b795b541933cef7a311`, reran mainline smoke successfully, removed worktree `../_codex_worktrees/phase8-ablation-and-perf-attempt-1`, and deleted branch `codex/phase8-ablation-and-perf/attempt-1`.
- [2026-04-21T15:12:25Z] Verified the merged Phase 8 baseline on `main@9c29e0803b709fdb6260c3653cbea5347c7a4015`, then created worktree `../_codex_worktrees/phase9-value-pack-attempt-1` on branch `codex/phase9-value-pack/attempt-1`.
- [2026-04-21T15:12:25Z] Bootstrapped the Phase 9 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; baseline help check and focused regression slice passed in the new worktree.
- [2026-04-21T15:12:25Z] Phase 9 TDD red step completed: `tests/test_phase9_value_pack.py` failed first because no scorecard generator or scorecard docs existed.
- [2026-04-21T15:12:25Z] Phase 9 green step completed: implemented `src/deep_research_agent/evals/value_scorecard.py`, `scripts/build_value_scorecard.py`, generated `docs/final/VALUE_SCORECARD.{md,json}`, and added `evals/reports/followup_metrics/README.md`.
- [2026-04-21T15:12:25Z] Phase 9 acceptance passed in the worktree: lint pass, broad regression slice pass (81 passed), CLI help pass, API smoke pass, and temp-root scorecard generation pass.
- [2026-04-21T15:12:25Z] Merged Phase 9 into `main` via `8f0f5e6e4a772f916918f7d77309d28b5ce0f76d`, reran the final mainline smoke successfully, removed worktree `../_codex_worktrees/phase9-value-pack-attempt-1`, deleted branch `codex/phase9-value-pack/attempt-1`, and confirmed `git status --short` stayed clean after the rerun.
