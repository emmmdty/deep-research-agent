# Benchmark Portfolio Run Status

## Static run info
- run_id: benchmark-run-20260422T082619Z
- main_repo_abs: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_branch: main
- worktrees_root: /tmp/_codex_worktrees
- started_at: 2026-04-22T08:26:19Z
- codex_model: gpt-5.4
- codex_reasoning_effort: medium
- sandbox_mode: workspace-write
- approval_policy: never

## Baseline import
- baseline_commit: 5f5d9b9f057c8eb985af2f0b0043a47183e78bbd
- baseline_release_manifest: evals/reports/phase5_local_smoke/release_manifest.json
- baseline_value_scorecard: docs/final/VALUE_SCORECARD.md
- benchmark_portfolio_run_started_from_clean_main: yes

## Command registry additions
- benchmark_runner: scripts/run_external_benchmark.py
- portfolio_summary_builder: scripts/build_benchmark_portfolio_summary.py
- facts_runner: scripts/run_facts_grounding.py
- longfact_safe_runner: scripts/run_longfact_safe.py
- longbench_runner: scripts/run_longbench_v2.py
- browsecomp_runner: scripts/run_browsecomp_guarded.py
- gaia_runner: scripts/run_gaia_subset.py

## Current overall status
- current_phase: phase14
- current_phase_slug: portfolio-docs-and-gate
- current_attempt: 1
- last_successful_phase: phase14
- overall_state: completed

## Worktree state
- active_branch: main
- active_worktree: /tmp/dra-benchmark-run
- main_clean_before_phase: yes
- post_merge_smoke_status: `ruff check .`, `pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase4_surfaces.py tests/test_cli_runtime.py tests/test_external_benchmarks.py`, `main.py eval run --suite company12`, the full external smoke pack under `/tmp/phase14_portfolio_reports`, and `scripts/build_benchmark_portfolio_summary.py --reports-root /tmp/phase14_portfolio_reports --output-root evals/external/reports/portfolio_summary --json` all passed on `/tmp/dra-benchmark-run`; repeated summary generation preserved file hashes and `git status --short --branch` stayed clean

## Local-only / ignored asset audit
- checked_paths: .env, .venv, .python-version, workspace/, .codex/, provider keys / benchmark cache / gated dataset cache
- missing_assets: none in the Phase 10 worktree after bootstrap
- recreated_assets:
- symlinked_assets: .env, .venv, workspace, venv_gptr, .codex/config.toml
- copied_assets:
- blockers_from_local_assets: none found in the Phase 10 worktree after bootstrap

## Phase ledger

### Phase 10 - scaffolding_and_facts
- status: completed
- attempts: 1
- summary: Added the shared external benchmark substrate, CLI `benchmark run`, FACTS Grounding smoke adapter/config/dataset, schema-validated artifact emission, and the first benchmark doc page without changing the native eval surface.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_external_benchmarks.py` -> pass (2 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py benchmark run --benchmark facts_grounding --split open --subset smoke --output-root /tmp/phase10_facts_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/phase10_company12_smoke --json` -> pass
- artifacts:
  - `src/deep_research_agent/evals/external/`
  - `evals/external/configs/facts_grounding_open_smoke.yaml`
  - `evals/external/dataset_manifests/facts_grounding_open_smoke.json`
  - `schemas/benchmark-*.schema.json`
  - `scripts/run_external_benchmark.py`
  - `scripts/run_facts_grounding.py`
  - `docs/benchmarks/FACTS_GROUNDING.md`
- blockers:
- notes:
  - The current sandbox cannot write the repository `.git` directory, so branch/worktree/commit orchestration runs inside `/tmp/dra-benchmark-run` and mirrors tracked file edits back to the primary workspace.
  - Merge target commit on writable `main`: `7e3e640950ddb77ec2eaa81fb82e1671fec08706`

### Phase 11 - longfact_safe
- status: completed
- attempts: 1
- summary: Added the LongFact / SAFE smoke adapter, config and dataset manifest, script shim, and docs page; the run emits official-style `precision`, `recall`, and `f1_at_k` plus backend logging in diagnostics.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_external_benchmarks.py` -> pass (3 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_longfact_safe.py --subset smoke --output-root /tmp/phase11_longfact_safe_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- artifacts:
  - `src/deep_research_agent/evals/external/benchmarks/longfact_safe.py`
  - `evals/external/configs/longfact_safe_smoke.yaml`
  - `evals/external/dataset_manifests/longfact_safe_smoke.json`
  - `scripts/run_longfact_safe.py`
  - `docs/benchmarks/LONGFACT_SAFE.md`
- blockers:
- notes:
  - The smoke path is deterministic and local; live SAFE judge/search backends remain future extensions and should emit blocked reports rather than fabricated scores when unavailable.

### Phase 12 - longbench_v2
- status: completed
- attempts: 1
- summary: Added the LongBench v2 short smoke adapter, medium-bucket blocked harness, script shim, config/dataset manifest, and docs page while keeping the output contract MCQ-focused instead of forcing report bundles.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_external_benchmarks.py` -> pass (4 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_longbench_v2.py --bucket short --subset smoke --output-root /tmp/phase12_longbench_short_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_longbench_v2.py --bucket medium --subset smoke --output-root /tmp/phase12_longbench_medium_smoke --json` -> pass (`status=blocked`)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- artifacts:
  - `src/deep_research_agent/evals/external/benchmarks/longbench_v2.py`
  - `evals/external/configs/longbench_v2_short_smoke.yaml`
  - `evals/external/dataset_manifests/longbench_v2_short_smoke.json`
  - `scripts/run_longbench_v2.py`
  - `docs/benchmarks/LONGBENCH_V2.md`
- blockers:
- notes:
  - The medium bucket is intentionally reported as blocked until a long-context backend is explicitly enabled; this is a supported Phase 12 outcome.

### Phase 13 - browsecomp_and_gaia
- status: completed
- attempts: 1
- summary: Added the integrity helper layer, BrowseComp guarded smoke adapter, GAIA supported-subset adapter, config/dataset manifests, script shims, and challenge-track docs including the shared integrity note.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_external_benchmarks.py` -> pass (6 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_browsecomp_guarded.py --subset smoke --output-root /tmp/phase13_browsecomp_guarded_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_gaia_subset.py --subset smoke_supported --output-root /tmp/phase13_gaia_supported_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- artifacts:
  - `src/deep_research_agent/evals/external/integrity/`
  - `src/deep_research_agent/evals/external/benchmarks/browsecomp.py`
  - `src/deep_research_agent/evals/external/benchmarks/gaia.py`
  - `evals/external/configs/browsecomp_guarded_smoke.yaml`
  - `evals/external/configs/gaia_supported_smoke.yaml`
  - `scripts/run_browsecomp_guarded.py`
  - `scripts/run_gaia_subset.py`
  - `docs/benchmarks/BROWSECOMP.md`
  - `docs/benchmarks/GAIA.md`
  - `docs/benchmarks/INTEGRITY.md`
- blockers:
- notes:
  - BrowseComp remains challenge-only and GAIA remains subset-first; neither adapter promotes itself into the authoritative release gate.

### Phase 14 - portfolio_docs_and_gate
- status: completed
- attempts: 1
- summary: Added the portfolio summary builder, reviewer-facing benchmark docs, committed summary artifacts under `evals/external/reports/portfolio_summary/`, README benchmark layering, and final-doc links while keeping the native Phase 5 pack as the only authoritative release gate.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase4_surfaces.py tests/test_cli_runtime.py tests/test_external_benchmarks.py` -> pass (69 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/phase14_main_company12_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_facts_grounding.py --split open --subset smoke --output-root /tmp/phase14_main_reports/facts_grounding_open_smoke --json` -> pass
  - full external smoke pack rerun to `/tmp/phase14_portfolio_reports` -> pass (`facts_grounding`, `longfact_safe`, `longbench_v2` short+medium, `browsecomp`, `gaia`)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_benchmark_portfolio_summary.py --reports-root /tmp/phase14_portfolio_reports --output-root evals/external/reports/portfolio_summary --json` -> pass
  - repeated summary rebuild kept `sha256sum evals/external/reports/portfolio_summary/portfolio_summary.json` stable -> pass
  - `git status --short --branch` on writable `main` -> clean (`## main...origin/main [ahead 15]`)
- artifacts:
  - `src/deep_research_agent/evals/external/summary.py`
  - `scripts/build_benchmark_portfolio_summary.py`
  - `docs/benchmarks/README.md`
  - `docs/benchmarks/PORTFOLIO.md`
  - `evals/external/reports/README.md`
  - `evals/external/reports/portfolio_summary/`
  - `README.md`
  - `docs/final/EXPERIMENT_SUMMARY.md`
  - `docs/final/VALUE_SCORECARD.md`
- blockers:
- notes:
  - LongBench v2 medium runs are now explicitly reported as `challenge_track` while the short bucket remains `external_regression`.
  - The committed portfolio summary is stable under repeated rebuilds because `generated_at` is preserved when the underlying summary content is unchanged.
  - Merge target commit on writable `main`: `e2d3223`

## Portfolio snapshot
- current_authoritative_gate: native Phase 5 local smoke suites (company12, industry12, trusted8, file8, recovery6)
- current_secondary_regression: facts_grounding open smoke harness is implemented
- current_external_regression: longfact_safe smoke and longbench_v2 short smoke are implemented
- current_challenge_tracks: browsecomp_guarded, gaia_supported_subset, and longbench_v2 medium/long are informative challenge tracks; medium currently emits a blocked harness when long-context capacity is unavailable
- implemented_adapters: facts_grounding, longfact_safe, longbench_v2, browsecomp, gaia
- deferred_adapters: facts private/blind submission, GAIA private submission, GAIA full multimodal coverage, LongBench official/full submissions, and fully measured live provider-routing deltas remain deferred
- open_integrity_risks: root AGENTS.md and benchmark overlay use different STATUS/phase paths; legacy benchmark/comparator diagnostics must stay distinct from the new external benchmark substrate; the primary workspace `.git` directory is read-only in this sandbox, so Git orchestration runs from the writable `/tmp` execution clone

## Decisions log
- [2026-04-22T07:33:43Z] Started benchmark portfolio control-layer preflight only; no worktree created and no benchmark phase started.
- [2026-04-22T07:33:43Z] Verified that all requested benchmark control docs exist locally under .agent/benchmark_portfolio/.
- [2026-04-22T07:33:43Z] Parsed .agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml successfully.
- [2026-04-22T07:33:43Z] Verified the native baseline artifacts still exist: main.py eval surface, Phase 5 release manifest, follow-up metrics, and native suite definitions.
- [2026-04-22T07:33:43Z] Detected that .agent/benchmark_portfolio/ was untracked on main during the first preflight attempt.
- [2026-04-22T07:33:43Z] Recorded first preflight verdict: NOT_READY.
- [2026-04-22T07:52:53Z] Reran benchmark portfolio control-layer preflight after benchmark control docs were committed on local main.
- [2026-04-22T07:52:53Z] Verified that git now tracks the benchmark control-layer files under .agent/benchmark_portfolio/.
- [2026-04-22T07:52:53Z] Parsed .agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml successfully on the current baseline commit.
- [2026-04-22T07:52:53Z] Verified the native baseline artifacts still exist: main.py eval surface, Phase 5 release manifest, experiment summary, value scorecard, and native suite definitions.
- [2026-04-22T07:52:53Z] Confirmed local main is clean for worktree creation; git status reports only main...origin/main [ahead 1].
- [2026-04-22T07:52:53Z] Carried forward a minor doc-boundary caution: benchmark overlay governs eval-layer expansion, while .agent/context/* remains the runtime/product contract.
- [2026-04-22T07:52:53Z] Recorded preflight verdict: READY_WITH_MINOR_DOC_FIXES.
- [2026-04-22T08:17:27Z] Re-verified the accepted baseline before Phase 10 start: `main.py --help`, `ruff check .`, and `main.py eval run --suite company12` all passed.
- [2026-04-22T08:19:00Z] The primary workspace `.git` directory and `../_codex_worktrees` root are not writable in this sandbox, so the benchmark run is executing from `/tmp/dra-benchmark-run` with worktrees under `/tmp/_codex_worktrees`.
- [2026-04-22T08:20:00Z] Created Phase 10 worktree `/tmp/_codex_worktrees/phase10-scaffolding-and-facts-attempt-1` on branch `codex/phase10-scaffolding-and-facts/attempt-1` and bootstrapped `.env`, `.venv`, `workspace`, `venv_gptr`, and `.codex/config.toml` via symlinks.
- [2026-04-22T08:24:30Z] Phase 10 TDD red step added `tests/test_external_benchmarks.py` and confirmed the new CLI/runner expectations failed before implementation (`2 failed`).
- [2026-04-22T08:25:38Z] Phase 10 implementation added the shared external benchmark substrate, FACTS Grounding smoke fixture/config, schema-validated manifests, and the new `benchmark run` CLI plus script shims.
- [2026-04-22T08:25:38Z] Phase 10 acceptance passed in the worktree: focused benchmark tests = `2 passed`, FACTS smoke artifact emission = pass, `ruff check .` = pass, and native `company12` smoke remained green.
- [2026-04-22T08:27:00Z] Merged Phase 10 into writable `main` via commit `7e3e640950ddb77ec2eaa81fb82e1671fec08706` and reran post-merge smoke successfully (`ruff check .`, `pytest -q tests/test_external_benchmarks.py`, FACTS smoke CLI, native `company12` smoke).
- [2026-04-22T08:29:00Z] Created Phase 11 worktree `/tmp/_codex_worktrees/phase11-longfact-safe-attempt-1` on branch `codex/phase11-longfact-safe/attempt-1` and bootstrapped `.env`, `.venv`, `workspace`, `venv_gptr`, and `.codex/config.toml` via symlinks.
- [2026-04-22T08:30:00Z] Phase 11 TDD red step extended `tests/test_external_benchmarks.py` with LongFact / SAFE smoke expectations and confirmed the missing adapter failed before implementation (`1 failed`).
- [2026-04-22T08:31:06Z] Phase 11 implementation added the LongFact / SAFE smoke adapter/config/dataset, backend logging, script shim, and docs page.
- [2026-04-22T08:31:06Z] Phase 11 acceptance passed in the worktree: focused benchmark tests = `3 passed`, `scripts/run_longfact_safe.py` = pass, and `ruff check .` = pass.
- [2026-04-22T08:31:50Z] Merged Phase 11 into writable `main` via commit `369e07da8d942c3307da7227780a253cd4155b0a` and reran post-merge smoke successfully (`ruff check .`, `pytest -q tests/test_external_benchmarks.py`, `scripts/run_longfact_safe.py`).
- [2026-04-22T08:33:00Z] Created Phase 12 worktree `/tmp/_codex_worktrees/phase12-longbench-v2-attempt-1` on branch `codex/phase12-longbench-v2/attempt-1` and bootstrapped `.env`, `.venv`, `workspace`, `venv_gptr`, and `.codex/config.toml` via symlinks.
- [2026-04-22T08:34:00Z] Phase 12 TDD red step extended `tests/test_external_benchmarks.py` with LongBench v2 short/medium expectations and confirmed the missing adapter failed before implementation (`1 failed`).
- [2026-04-22T08:35:00Z] Phase 12 implementation added the LongBench v2 short smoke adapter, medium blocked harness, script shim, config/dataset manifest, and docs page.
- [2026-04-22T08:35:00Z] Phase 12 acceptance passed in the worktree: focused benchmark tests = `4 passed`, LongBench short smoke = pass, LongBench medium blocked harness = pass, and `ruff check .` = pass.
- [2026-04-22T08:36:00Z] Merged Phase 12 into writable `main` via commit `477c7920d19ef3caf79c513a4e0153d84527d9c8` and reran post-merge smoke successfully (`ruff check .`, `pytest -q tests/test_external_benchmarks.py`, `scripts/run_longbench_v2.py` short+medium).
- [2026-04-22T08:37:00Z] Created Phase 13 worktree `/tmp/_codex_worktrees/phase13-browsecomp-and-gaia-attempt-1` on branch `codex/phase13-browsecomp-and-gaia/attempt-1` and bootstrapped `.env`, `.venv`, `workspace`, `venv_gptr`, and `.codex/config.toml` via symlinks.
- [2026-04-22T08:38:00Z] Phase 13 TDD red step extended `tests/test_external_benchmarks.py` with BrowseComp integrity and GAIA capability-gated expectations and confirmed both missing adapters failed before implementation (`2 failed`).
- [2026-04-22T08:39:00Z] Phase 13 implementation added the shared integrity guard helpers, BrowseComp guarded smoke adapter, GAIA supported-subset adapter, config/dataset manifests, script shims, and challenge-track docs.
- [2026-04-22T08:39:00Z] Phase 13 acceptance passed in the worktree: focused benchmark tests = `6 passed`, BrowseComp guarded smoke = pass, GAIA supported smoke = pass, and `ruff check .` = pass.
- [2026-04-22T08:40:00Z] Merged Phase 13 into writable `main` via commit `1ccdf78e37880271e5c1d037d3a7dcb016e3b52f` and reran post-merge smoke successfully (`ruff check .`, `pytest -q tests/test_external_benchmarks.py`, BrowseComp guarded smoke, GAIA supported smoke).
- [2026-04-22T08:44:00Z] Created Phase 14 worktree `/tmp/_codex_worktrees/phase14-portfolio-docs-and-gate-attempt-1` on branch `codex/phase14-portfolio-docs-and-gate/attempt-1` and bootstrapped `.env`, `.venv`, `workspace`, `venv_gptr`, and `.codex/config.toml` via symlinks.
- [2026-04-22T08:45:00Z] Phase 14 TDD red step extended `tests/test_external_benchmarks.py` with portfolio summary generation coverage and confirmed the missing summary module failed before implementation (`ModuleNotFoundError`).
- [2026-04-22T08:48:00Z] Phase 14 implementation added `src/deep_research_agent/evals/external/summary.py`, `scripts/build_benchmark_portfolio_summary.py`, reviewer-facing benchmark docs, and committed portfolio summary artifacts under `evals/external/reports/portfolio_summary/`.
- [2026-04-22T08:51:00Z] Added a regression fix so LongBench v2 medium manifests are emitted as `challenge_track` instead of `external_regression`, and the summary merge logic now preserves static catalog identity fields while overlaying discovered run status.
- [2026-04-22T08:53:00Z] Phase 14 acceptance passed in the worktree: `ruff check .`, the 69-test regression slice, native `company12` smoke, the full external smoke pack, and portfolio summary generation all passed; repeated summary rebuilds were byte-stable.
- [2026-04-22T08:54:00Z] Merged Phase 14 into writable `main` via commit `e2d3223` and reran post-merge smoke successfully (`ruff check .`, the 69-test regression slice, native `company12` smoke, the full external smoke pack, summary regeneration, and clean `git status`).
