# Phase 0 — Read and model

## Objective
Read the repository and all concise context files.
Freeze the real execution backlog against the live repo.
Do not start the large refactor before the backlog, file impact list, command registry, and risk log exist.

## Required reading
- all `.agent/context/*`
- top-level README
- key repo entrypoints
- runtime/job code
- connector code
- auditor code
- evaluation code
- test layout
- packaging/config files

## Required outputs
Create or update:
- `.agent/EXECUTION_BACKLOG.md`
- `.agent/STATUS.md`
- this phase file with any clarified sub-steps
- docs note if the repo reality differs materially from the context docs

## Must capture
- keep assets
- migrate assets
- archive assets
- delete assets
- new modules to add
- first P0 implementation tranche
- file/dir impact list
- command registry
- known risks and unknowns

## Constraints
- no major code movement yet except minimal scaffolding needed to enable the next phase
- no speculative rewrites
- no skipping repo audit

## Acceptance
This phase passes only when:
- `.agent/EXECUTION_BACKLOG.md` exists
- `.agent/STATUS.md` has a real command registry
- keep/migrate/archive/delete lists are grounded in the live repo
- a file impact map exists
- risks are recorded
- the next phases have concrete acceptance commands

## Validation
Run at least:
- repo tree inspection commands
- package/config inspection commands
- current test discovery commands
- one baseline smoke command if safe

Record the exact commands and outcomes in `.agent/STATUS.md`.

## Attempt 1 clarified sub-steps

1. Verify `main` baseline from the main worktree before creating a Phase 0 worktree.
2. Create `../_codex_worktrees/phase0-read-and-model-attempt-1` from branch `codex/phase0-read-and-model/attempt-1`.
3. Bootstrap missing local-only assets by explicit inspection, not by `git status`.
4. Freeze repo-specific decisions that were still open after preflight:
   - unmapped top-level directory handling
   - source-profile migration strategy
   - documentation authority split
5. Write `.agent/EXECUTION_BACKLOG.md` with grounded keep/migrate/archive/delete lists, file impact map, risk log, command registry, and phase acceptance commands.
6. Refresh `.agent/STATUS.md` to reflect the real execution run rather than the preflight-only state.
7. Re-run baseline safe validation in the Phase 0 worktree.

## Attempt 1 validation commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest --collect-only -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py`
