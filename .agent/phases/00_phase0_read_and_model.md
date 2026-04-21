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