# Phase 6 — Finalize and handoff

## Objective
Finish the run cleanly and leave the repo in a reviewable, explainable state.

## Required outcomes
- final cleanup
- final architecture/docs consistency pass
- `FINAL_CHANGE_REPORT.md`
- experiment/result summary
- unresolved blocker summary if anything remains
- final repository health check on `main`

## Must produce
- concise summary of:
  - what changed
  - what was archived
  - what was deleted
  - what remains
  - how to run the system
  - how to reproduce the key eval/demo flow

## Acceptance
This phase passes only when:
- `main` is clean and passes final smoke validation
- final docs exist
- final report exists
- remaining gaps are explicitly documented rather than hidden

## Validation
Run at least:
- final lint/smoke subset on `main`
- final CLI/API demo command checks
- final artifact path checks

## Implementation notes
- Added `FINAL_CHANGE_REPORT.md` at the repo root as the final handoff document.
- Added `docs/final/EXPERIMENT_SUMMARY.md` to summarize the committed Phase 5 smoke results and release-manifest evidence.
- Updated `README.md` and `docs/development.md` so the final handoff documents are discoverable from the main developer entrypoints.
- Final Phase 6 validation in the worktree passed:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_phase5_evals.py tests/test_release_gate.py tests/test_release_runner.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase4_surfaces.py tests/test_cli_runtime.py tests/test_basic.py tests/test_scripts.py` -> pass (98 passed)
  - CLI demo: `submit --no-worker` + `status --json` -> pass
  - API demo: `POST /v1/research/jobs` -> `202`, `GET /v1/research/jobs/{job_id}` -> `200`
  - artifact/doc path checks -> pass
