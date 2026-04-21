# Phase 3 — Connectors, evidence, audit, reporting

## Objective
Implement the evidence-first research pipeline from source acquisition to report bundle.

## Required outcomes
- search / fetch / file-ingest abstraction
- at least these first-class connectors:
  - web
  - github
  - arxiv
  - files
- source policy integration
- snapshot storage
- document normalization/chunking
- evidence fragments
- claim objects
- support/conflict edges
- audit gate
- review queue if blocked
- report bundle rendering

## Must produce
- one end-to-end research flow
- artifacts that let a reader trace:
  `claim -> evidence -> snapshot/source`
- concrete output files such as:
  - report.md
  - report_bundle.json
  - claims.json
  - sources.json
  - audit_decision.json
  - trace.jsonl
  - manifest.json

## Constraints
- report prose is not the source of truth
- bundle JSON is the source of truth
- unsupported claims must not appear as confident findings

## Acceptance
This phase passes only when:
- one full research job can run end to end
- the emitted artifacts are real and inspectable
- claim/evidence/snapshot traceability exists
- blocked or low-support situations are surfaced through audit artifacts
- focused integration tests pass

## Validation
Run at least:
- integration tests for connectors/policy/snapshot
- integration tests for claim/audit/reporting path
- one real or frozen-snapshot research job smoke
- artifact schema validation

## Attempt 1 execution notes

### Scope completed
- promoted live connector implementations into `src/deep_research_agent/connectors/`
- promoted audit pipeline/store/models into `src/deep_research_agent/auditor/`
- promoted report compiler/schema helpers into `src/deep_research_agent/reporting/`
- promoted the evidence-store implementation into `src/deep_research_agent/evidence_store/store.py`
- converted top-level `connectors/`, `auditor/`, `artifacts/`, and `memory/evidence_store.py` into compatibility shims so the runtime path resolves through `src/`
- extended the report compiler to emit `report.html`, `claims.json`, `sources.json`, `audit_decision.json`, and `manifest.json` alongside `report_bundle.json` and `trace.jsonl`

### Runtime decisions captured during execution
- kept `report_bundle.json` as the authoritative truth object; the new sidecars are derived views and index files over that bundle
- added `artifact-manifest.schema.json` so `manifest.json` is a validated contract rather than an ad hoc index file
- used a frozen-snapshot end-to-end smoke for acceptance so Phase 3 proof does not depend on live web availability or collector heuristics
- kept the public CLI surface unchanged in this phase; docs were updated only to reflect the expanded artifact set and validation path

### Validation evidence
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py` -> pass (`55 passed`)
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_basic.py tests/test_scripts.py` -> pass (`82 passed`)
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
- frozen-snapshot end-to-end smoke under a temp workspace -> pass:
  - completed job emitted `report.md`, `bundle/report.html`, `bundle/report_bundle.json`, `bundle/claims.json`, `bundle/sources.json`, `bundle/audit_decision.json`, `bundle/manifest.json`, and `bundle/trace.jsonl`
  - schema validation passed for both `report-bundle` and `artifact-manifest`
  - smoke bundle counts: `source_count=1`, `snapshot_count=1`, `evidence_count=1`
