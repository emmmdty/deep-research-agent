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