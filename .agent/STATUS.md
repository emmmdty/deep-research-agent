# Run Status

## Static run info
- run_id: execute-20260421T114914Z
- main_repo_abs: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_branch: main
- worktrees_root: ../_codex_worktrees
- started_at: 2026-04-21T11:49:14Z
- codex_model: gpt-5.4
- codex_reasoning_effort: medium
- sandbox_mode: danger-full-access
- approval_policy: never

## Command registry
- lint: UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
- format_check: not documented separately
- typecheck: not configured in the current repo
- unit_tests: UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
- integration_tests: UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py
- e2e_smoke: phase-specific synthetic or frozen-snapshot job smoke; no single global e2e command exists yet
- build: none documented
- api_smoke: not applicable yet; current public surface has no supported HTTP API
- cli_smoke: UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help
- eval_runner: UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
- test_collect: UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q
- focused_runtime_regressions: UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py

## Current overall status
- current_phase: phase4_surface_docs
- current_phase_slug: phase4-surface-docs
- current_attempt: 1
- last_successful_phase: phase3_pipeline
- overall_state: phase4_acceptance_passed

## Worktree state
- active_branch: codex/phase4-surface-docs/attempt-1
- active_worktree: /home/tjk/myProjects/internship-projects/_codex_worktrees/phase4-surface-docs-attempt-1
- main_clean_before_phase: yes
- main_baseline_commit: 4a7995b6eec6d47a2d84efba750fcd53e55f418c
- post_merge_smoke_status:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_basic.py tests/test_scripts.py` -> pass (82 passed)

## Local-only / ignored asset audit
- checked_paths: .env, .python-version, .venv, .codex/config.toml, workspace/, venv_gptr/
- missing_assets: none in the current main worktree
- recreated_assets:
- symlinked_assets:
  - .env -> /home/tjk/myProjects/internship-projects/03-deep-research-agent/.env
  - .venv -> /home/tjk/myProjects/internship-projects/03-deep-research-agent/.venv
  - .codex/config.toml -> /home/tjk/myProjects/internship-projects/03-deep-research-agent/.codex/config.toml
  - workspace -> /home/tjk/myProjects/internship-projects/03-deep-research-agent/workspace
  - venv_gptr -> /home/tjk/myProjects/internship-projects/03-deep-research-agent/venv_gptr
- copied_assets:
- blockers_from_local_assets: none in the current main worktree; Phase 2 lifecycle smoke and Phase 3 frozen-snapshot smoke both used isolated temp workspaces to avoid writing runtime artifacts into the shared `workspace/` symlink

## Phase ledger

### Phase 0 - read_and_model
- status: completed
- attempts: 1
- summary: Phase 0 execution backlog, file-impact map, command registry, risk log, and open-decision resolution are frozen on `main`; phase worktree validation and post-merge smoke both passed.
- acceptance_checks:
  - baseline on main: `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - baseline on main: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q` -> pass
  - phase0 worktree: `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - phase0 worktree: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q` -> pass (171 tests collected)
  - phase0 worktree: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - phase0 worktree: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py` -> pass (45 passed)
- artifacts:
  - .agent/PREFLIGHT_DOC_AUDIT.md
  - .agent/EXECUTION_BACKLOG.md
- blockers: none blocking Phase 0 start
- notes:
  - Phase 0 froze unmapped-directory handling and source-profile migration strategy.
  - Active phase file now includes clarified sub-steps and validation commands.
  - Merge target commit on `main`: `2aca4d7e28aaa8a825c864c4e3795fc211ae404f`
  - Next action: create the fresh Phase 1 worktree after cleaning up the Phase 0 worktree and branch.

### Phase 1 - structure
- status: completed
- attempts: 1
- summary: Created the canonical `src/deep_research_agent/` package tree, moved `agents/` and `workflows/` under `legacy/`, made `main.py` a thin wrapper, updated packaging/imports so the new src package is importable, and verified the structure on `main`.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import deep_research_agent; print(deep_research_agent.__file__)"`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- artifacts:
  - `tests/test_phase1_structure_rebuild.py`
  - `src/deep_research_agent/`
  - `legacy/agents/`
  - `legacy/workflows/`
- blockers:
- notes:
  - Focused validation passed: `tests/test_phase1_structure_rebuild.py`, `tests/test_cli_runtime.py`, `tests/test_phase2_jobs.py`, `tests/test_phase3_connectors.py`, `tests/test_phase4_auditor.py` -> 51 passed.
  - Merge target landed on `main`; next action is Phase 2 in a fresh worktree.

### Phase 2 - runtime_provider
- status: completed
- attempts: 1
- summary: Canonicalized the runtime/service/store/orchestrator stack, introduced the provider routing layer for OpenAI/Anthropic/compatible backends, switched source-profile handling to the Task 2 contract, updated the CLI public lifecycle commands, and fixed no-worker stale recovery so deterministic local control-plane smoke passes.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_cli_runtime.py` -> pass (30 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_basic.py tests/test_scripts.py` -> pass (81 passed)
  - isolated lifecycle smoke (`submit -> status -> cancel -> retry -> resume -> refine -> status`, all mutating commands with `--no-worker`) -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- artifacts:
  - `src/deep_research_agent/common/source_profiles.py`
  - `src/deep_research_agent/providers/`
  - `src/deep_research_agent/research_jobs/`
  - `tests/test_phase2_providers.py`
  - canonical source-profile YAMLs under `policies/source-profiles/`
- blockers:
- notes:
  - Added `langchain-anthropic` to `pyproject.toml` / `uv.lock` for native Anthropic provider support.
  - `services/research_jobs/*` and `llm/provider.py` now proxy to the canonical `src/` implementations to keep the migration phase-scoped.
  - The first CLI smoke failure exposed that `recover_stale_jobs()` was auto-starting intentionally idle `--no-worker` jobs on the next CLI invocation; repaired in the same attempt and covered with a regression test.
  - Merge target commit on `main`: `fd7819a`
  - Phase 2 worktree was removed and branch `codex/phase2-runtime-provider/attempt-1` was deleted after merge.

### Phase 3 - pipeline
- status: completed
- attempts: 1
- summary: Promoted connectors, evidence-store, auditor, and reporting logic into the canonical `src/` package, converted top-level packages into compatibility shims, and upgraded bundle emission so completed jobs now write validated sidecar artifacts (`report.html`, `claims.json`, `sources.json`, `audit_decision.json`, `manifest.json`) in addition to the authoritative `report_bundle.json`.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py` -> pass (55 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_basic.py tests/test_scripts.py` -> pass (82 passed)
  - frozen-snapshot end-to-end job smoke with one source, one snapshot, and one evidence fragment -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- artifacts:
  - `src/deep_research_agent/connectors/`
  - `src/deep_research_agent/auditor/`
  - `src/deep_research_agent/reporting/bundle/compiler.py`
  - `src/deep_research_agent/reporting/schemas.py`
  - `src/deep_research_agent/evidence_store/store.py`
  - `schemas/artifact-manifest.schema.json`
- blockers:
- notes:
  - Top-level `connectors/`, `auditor/`, `artifacts/`, and `memory/evidence_store.py` now forward to canonical `src/` modules instead of carrying the main implementation.
  - `emit_report_artifacts()` now validates `report_bundle.json`, writes the sidecar artifact set, and emits `manifest.json` as the index contract for later API/artifact serving work.
  - Updated `docs/development.md` and `docs/architecture.md` so the documented Phase 3 validation path matches the expanded artifact set.
  - Merge target commit on `main`: `f211d5a`
  - Phase 3 worktree was removed and branch `codex/phase3-pipeline/attempt-1` was deleted after merge.

### Phase 4 - surface_docs
- status: completed
- attempts: 1
- summary: Added the local FastAPI surface over the deterministic runtime, introduced `bundle` and `batch run` CLI commands, exposed stable artifact-name routing without leaking workspace paths, and rewrote the public docs/ADRs/migration notes to match the implemented Phase 4 surface.
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py tests/test_cli_runtime.py` -> pass (10 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - OpenAPI smoke (`uv run python - <<'PY' ... app.openapi() ... PY`) -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase4_surfaces.py tests/test_cli_runtime.py` -> pass (60 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase4_surfaces.py tests/test_basic.py tests/test_scripts.py` -> pass (87 passed)
- artifacts:
  - `src/deep_research_agent/gateway/api.py`
  - `src/deep_research_agent/gateway/contracts.py`
  - `src/deep_research_agent/gateway/artifacts.py`
  - `src/deep_research_agent/gateway/batch.py`
  - `tests/test_phase4_surfaces.py`
  - `docs/adr/adr-0008-http-api-surface.md`
  - `docs/adr/adr-0009-batch-and-artifact-contract.md`
  - `docs/migrations/phase4-surface-migration.md`
- blockers:
- notes:
  - The HTTP API is intentionally local and still backed by SQLite/filesystem runtime semantics; it is a supported local surface, not a server-grade multi-tenant service.
  - Public API responses now use stable artifact URLs instead of raw workspace paths; the CLI keeps its developer-oriented JSON output style.
  - Review actions are append-only, recorded in runtime events, written to `review_actions.jsonl`, and mirrored into `audit_decision.json` / `trace.jsonl` when those artifacts already exist.

### Phase 5 - evals_release
- status: pending
- attempts: 0
- summary: Rebuild tests/evals/release gates around claim-centric metrics and runnable manifests.
- acceptance_checks:
  - lint
  - unit tests
  - integration tests
  - e2e smoke
  - one reliability suite
  - one policy suite
  - one file-ingest suite
  - one company task and one industry task with saved bundles
- artifacts:
- blockers:
- notes:

### Phase 6 - finalize
- status: pending
- attempts: 0
- summary: Final cleanup, final report artifacts, final docs consistency pass, and main-branch health verification.
- acceptance_checks:
  - final lint/smoke subset on `main`
  - final CLI/API demo command checks
  - final artifact/doc existence checks
- artifacts:
- blockers:
- notes:

## Decisions log
- [2026-04-21T11:31:48Z] User requested control-layer preflight only; no worktrees, merges, or implementation phases started.
- [2026-04-21T11:31:48Z] Verified all required control documents exist at the requested paths.
- [2026-04-21T11:31:48Z] Parsed .agent/context/TASK2_SPEC.yaml successfully.
- [2026-04-21T11:31:48Z] Verified phase file order matches 00 through 06 and titles align with the plan.
- [2026-04-21T11:31:48Z] Executed safe validation only: `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q` (171 tests collected).
- [2026-04-21T11:31:48Z] Final verification pass confirmed control-doc presence, YAML parseability, phase-file ordering, balanced fenced blocks, and the written readiness verdict (`control_docs_verified`).
- [2026-04-21T11:31:48Z] Applied minimal doc fixes in AGENTS.md, .agent/IMPLEMENT.md, .agent/phases/04_phase4_surface_docs.md, .agent/context/METHODOLOGY.md, .agent/context/EVAL_AND_GATES.md, .agent/context/REPO_AUDIT.md, and .agent/context/TASK1_OUTPUT_FULL.md.
- [2026-04-21T11:31:48Z] Preflight readiness verdict: READY_WITH_MINOR_DOC_FIXES.
- [2026-04-21T11:49:14Z] Started the full autonomous execution run from Phase 0 in worktree `../_codex_worktrees/phase0-read-and-model-attempt-1` on branch `codex/phase0-read-and-model/attempt-1`.
- [2026-04-21T11:49:14Z] Verified `main` baseline before creating the worktree using `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q`.
- [2026-04-21T11:49:14Z] Bootstrapped missing local-only assets in the Phase 0 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; tracked `.python-version` was already present.
- [2026-04-21T11:49:14Z] Re-ran safe validation in the Phase 0 worktree: CLI help pass, pytest collect pass, ruff pass, focused runtime regressions pass (45 passed).
- [2026-04-21T11:49:14Z] Phase 0 froze handling for unmapped directories, source-profile migration, command registry, phase acceptance commands, and file-impact mapping in `.agent/EXECUTION_BACKLOG.md`.
- [2026-04-21T11:49:14Z] Phase 0 acceptance passed in the phase worktree; next action is commit + merge + main smoke before advancing to Phase 1.
- [2026-04-21T11:52:03Z] Merged Phase 0 into `main` via commit `2aca4d7e28aaa8a825c864c4e3795fc211ae404f` and reran main smoke successfully (`main.py --help`, `pytest --collect-only -q`, `ruff check .`).
- [2026-04-21T11:52:03Z] Verified Phase 0 outputs on `main` before opening Phase 1, then created worktree `../_codex_worktrees/phase1-structure-attempt-1` on branch `codex/phase1-structure/attempt-1`.
- [2026-04-21T11:52:03Z] Bootstrapped local-only assets in the Phase 1 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`.
- [2026-04-21T11:52:03Z] Phase 1 TDD red step: added `tests/test_phase1_structure_rebuild.py` and confirmed it failed before the structure rebuild (`3 failed`).
- [2026-04-21T11:52:03Z] Phase 1 structure rebuild created `src/deep_research_agent/`, moved `agents/` and `workflows/` under `legacy/`, added the canonical package wrappers, and converted `main.py` to a thin wrapper over `deep_research_agent.gateway.cli`.
- [2026-04-21T11:52:03Z] Phase 1 validation passed in the worktree: package import smoke, CLI help, `ruff check .`, and focused regressions (`51 passed`).
- [2026-04-21T12:00:00Z] Phase 1 first merge exposed a post-merge test assumption mismatch caused by lingering top-level `__pycache__` directories; repaired on the same phase branch by tightening `tests/test_phase1_structure_rebuild.py` to assert absence of live Python modules rather than directory shells.
- [2026-04-21T12:00:00Z] Final Phase 1 post-merge smoke on `main` passed (`main.py --help`, `ruff check .`, focused regressions = `51 passed`).
- [2026-04-21T12:00:00Z] Verified the merged Phase 1 baseline on `main`, then created Phase 2 worktree `../_codex_worktrees/phase2-runtime-provider-attempt-1` on branch `codex/phase2-runtime-provider/attempt-1`.
- [2026-04-21T12:00:00Z] Bootstrapped local-only assets in the Phase 2 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; tracked `.python-version` was already present.
- [2026-04-21T12:32:04Z] Phase 2 promoted the canonical runtime modules under `src/deep_research_agent/research_jobs/`, added canonical provider routing under `src/deep_research_agent/providers/`, switched public source-profile names to the Task 2 contract, and updated the public CLI/runtime docs.
- [2026-04-21T12:32:04Z] Phase 2 acceptance initially exposed a deterministic smoke bug: `recover_stale_jobs()` treated intentionally idle `--no-worker` jobs as stale on the next CLI command and auto-spawned a worker. Repaired in-attempt by skipping recovery for jobs with no lease, pid, or heartbeat and by adding a regression test.
- [2026-04-21T12:32:04Z] Final Phase 2 validation passed in the worktree: focused runtime/CLI regressions (`30 passed`), broader regression suite (`81 passed`), `ruff check .`, and isolated lifecycle smoke with `submit/status/cancel/retry/resume/refine` while preserving `worker_pid == null`.
- [2026-04-21T12:35:00Z] Merged Phase 2 into `main` via commit `fd7819a`, reran main smoke successfully (`main.py --help`, `ruff check .`, broader regression suite = `81 passed`), removed worktree `../_codex_worktrees/phase2-runtime-provider-attempt-1`, and deleted branch `codex/phase2-runtime-provider/attempt-1`.
- [2026-04-21T12:35:00Z] Verified the merged Phase 2 baseline on `main`, then created Phase 3 worktree `../_codex_worktrees/phase3-pipeline-attempt-1` on branch `codex/phase3-pipeline/attempt-1`.
- [2026-04-21T12:35:00Z] Bootstrapped local-only assets in the Phase 3 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; tracked `.python-version` was already present.
- [2026-04-21T12:50:14Z] Phase 3 promoted connectors, auditor, reporting, and evidence-store implementations into the canonical `src/` package and converted the legacy top-level packages into compatibility shims.
- [2026-04-21T12:50:14Z] Phase 3 extended the report compiler to emit `report.html`, `claims.json`, `sources.json`, `audit_decision.json`, and `manifest.json`, and introduced `schemas/artifact-manifest.schema.json` to validate the emitted manifest contract.
- [2026-04-21T12:50:14Z] Final Phase 3 validation passed in the worktree: focused runtime/audit regressions (`55 passed`), broader regression suite (`82 passed`), `ruff check .`, CLI help smoke, and a frozen-snapshot end-to-end job smoke with `source_count=1`, `snapshot_count=1`, and `evidence_count=1`.
- [2026-04-21T12:52:09Z] Merged Phase 3 into `main` via commit `f211d5a`, reran main smoke successfully (`main.py --help`, `ruff check .`, broader regression suite = `82 passed`), reran the frozen-snapshot smoke on `main`, removed worktree `../_codex_worktrees/phase3-pipeline-attempt-1`, and deleted branch `codex/phase3-pipeline/attempt-1`.
- [2026-04-21T12:52:09Z] Verified the merged Phase 3 baseline on `main`, then created Phase 4 worktree `../_codex_worktrees/phase4-surface-docs-attempt-1` on branch `codex/phase4-surface-docs/attempt-1`.
- [2026-04-21T12:52:09Z] Bootstrapped local-only assets in the Phase 4 worktree by symlinking `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr`; tracked `.python-version` was already present.
- [2026-04-21T12:52:09Z] Phase 4 design baseline reuses the approved repository specs (`PROJECT_SPEC.md`, `TASK2_SPEC.yaml`, `04_phase4_surface_docs.md`) and focuses implementation on three public surfaces: HTTP API, CLI bundle/batch commands, and reproducible docs/ADRs.
- [2026-04-21T12:52:09Z] Phase 4 TDD red step: added `tests/test_phase4_surfaces.py`, extended `tests/test_cli_runtime.py` for `bundle` and `batch run`, and removed the obsolete `tests/test_phase6_api_readiness.py` that enforced the pre-Phase-4 “no HTTP API” contract.
- [2026-04-21T12:52:09Z] Implemented `src/deep_research_agent/gateway/api.py`, `contracts.py`, `artifacts.py`, and `batch.py`; added review recording to `ResearchJobService`; and extended the CLI with `bundle` plus `batch run`.
- [2026-04-21T12:52:09Z] Rewrote the public docs to match the new surface (`README.md`, `README.zh-CN` note, `docs/architecture.md`, `docs/development.md`, `specs/api-readiness-contract.md`) and added Phase 4 ADRs plus a migration note.
- [2026-04-21T12:52:09Z] Phase 4 acceptance passed in the worktree: focused API/CLI/schema regressions (`10 passed`), runtime/auditor/public-surface slice (`60 passed`), broader smoke suite (`87 passed`), `ruff check .`, CLI help smoke, and OpenAPI route smoke.
