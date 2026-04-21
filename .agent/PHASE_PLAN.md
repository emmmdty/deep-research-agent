# Phase Plan

## Execution order
Run phases strictly in this order:

0. Read and model
1. Structure rebuild
2. Runtime and provider layer
3. Connectors, evidence, audit, reporting
4. API, CLI, batch, docs
5. Tests, evals, release gates
6. Finalize and handoff

Do not skip a phase.
Do not advance on partial acceptance.

## Phase 0
Goal:
- read the repo and context docs
- freeze the execution backlog
- map file impact and risks
- discover actual test/lint/build commands
- update the plan if the live repo differs from expectations

Outputs:
- `.agent/EXECUTION_BACKLOG.md`
- updated `.agent/STATUS.md`
- revised phase-specific acceptance commands where needed

## Phase 1
Goal:
- create the target top-level boundaries
- establish `src/` layout
- move/archive legacy
- simplify package entrypoints

Outputs:
- new package structure
- archived legacy tree
- updated packaging/import paths

## Phase 2
Goal:
- implement deterministic job lifecycle
- implement provider abstraction
- implement config/schema foundations
- separate `status` and `audit_gate_status`

Outputs:
- runnable runtime core
- provider router
- local profile smoke path

## Phase 3
Goal:
- implement connector contracts
- implement snapshot/document/evidence/claim pipeline
- implement audit gate
- implement report bundle rendering

Outputs:
- end-to-end evidence-first research job
- audit artifacts
- report bundle artifacts

## Phase 4
Goal:
- implement public HTTP API
- stabilize CLI and batch entrypoints
- update docs/ADR/development guides

Outputs:
- API endpoints
- docs matching reality
- reproducible demo commands

## Phase 5
Goal:
- implement tests, eval suites, release gates
- run smoke/low-cost experiments locally
- run or prepare heavy eval harnesses

Outputs:
- test suite coverage
- eval outputs and manifests
- release checklist

## Phase 6
Goal:
- final cleanup
- final reports
- unresolved blockers
- final handoff docs

Outputs:
- `FINAL_CHANGE_REPORT.md`
- experiment summary
- blocker summary if any