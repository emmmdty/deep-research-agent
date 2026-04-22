# Phase 16 — Implement focused optimization

## Objective
Implement one focused optimization based on the selected target.

## Allowed optimization scopes
- improve weakest suite quality
- improve weakest suite provenance/grounding
- improve file-ingest determinism or evidence linkage
- improve trusted-only enforcement/clarity
- improve industry/company reasoning artifacts and rubrics
- improve recovery/control-plane clarity or robustness
- improve native benchmark reporting if the benchmark is saturated but under-explains value
- improve benchmark discriminativeness if all current suites are too easy

## Constraints
- exactly one target area
- no external benchmark work
- no provider-backed full native work
- keep smoke_local behavior intact
- keep regression_local task counts intact unless the chosen target explicitly requires harder tasks and the task count remains unchanged or increases

## Required outputs
- code/doc changes implementing the chosen optimization
- any updated fixtures/rubrics/tasks if the optimization target is benchmark discriminativeness or suite quality
- updated tests covering the changed behavior

## Acceptance
This phase passes only when:
- the chosen target has an actual implementation change
- touched tests pass
- smoke_local is not broken
- the selected suite or reporting surface is measurably changed in a way that Phase 17 can compare

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused tests for touched modules
- at least one smoke_local command for guardrail
- at least one affected regression_local command for the target suite
