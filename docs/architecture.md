# Deep Research Agent Architecture

This document describes the current implemented architecture after Phase 4.

## System Boundary

The supported system is an evidence-first research runtime with three public entrypoints:

- developer CLI
- local HTTP API
- batch submission path

All three surfaces share the same deterministic runtime:

- `ResearchJobService`
- SQLite job store
- append-only events
- checkpoint files
- filesystem report artifacts

The legacy LangGraph workflow remains archived and compatibility-only. It is not the supported product boundary.

## Canonical Flow

```text
submit request
  -> job runtime record
  -> initial checkpoint
  -> optional worker spawn
  -> orchestrator stages
  -> claim audit
  -> report bundle + sidecars
  -> status / events / artifacts exposed through CLI and API
```

## Runtime Stages

The deterministic control plane advances jobs through:

- `created`
- `clarifying`
- `planned`
- `collecting`
- `normalizing`
- `extracting`
- `claim_auditing`
- `synthesizing`
- `rendering`
- `completed`

Side states:

- `failed`
- `cancelled`

`status` and `audit_gate_status` are intentionally separate:

- lifecycle status answers whether execution finished
- audit gate answers whether critical claims are blocked, passed, or still pending manual review

## Main Modules

### `src/deep_research_agent/research_jobs/`

Owns the deterministic runtime:

- job records
- event log
- checkpoints
- worker lease and heartbeat
- cancel / retry / resume / refine
- stale recovery
- orchestrator stage execution

### `src/deep_research_agent/connectors/`

Owns the document ingestion boundary:

- connector registry
- search / fetch / file-ingest contracts
- snapshot persistence
- URI safety checks
- legacy tool adapters

### `policies/`

Owns source governance:

- source profiles
- allow / deny domain rules
- fetch budgets
- policy overrides

### `src/deep_research_agent/auditor/`

Owns claim-level audit:

- claim graph
- claim support edges
- conflict sets
- critical-claim review queue
- audit sidecars under `audit/`

### `src/deep_research_agent/reporting/`

Owns report delivery:

- `report_bundle.json`
- `report.html`
- `claims.json`
- `sources.json`
- `audit_decision.json`
- `manifest.json`
- `trace.jsonl`

`report_bundle.json` is the authoritative machine-readable output.

### `src/deep_research_agent/gateway/`

Owns public surfaces:

- `cli.py` for developer commands
- `api.py` for the local FastAPI app
- `batch.py` for batch file loading and shared batch semantics
- `contracts.py` for stable public request/response models
- `artifacts.py` for stable artifact-name resolution

## Public Surface Contract

### CLI

Supported commands:

- `submit`
- `status`
- `watch`
- `cancel`
- `retry`
- `resume`
- `refine`
- `bundle`
- `batch run`

### HTTP API

Implemented endpoints:

- `POST /v1/research/jobs`
- `GET /v1/research/jobs/{job_id}`
- `GET /v1/research/jobs/{job_id}/events`
- `POST /v1/research/jobs/{job_id}:cancel`
- `POST /v1/research/jobs/{job_id}:retry`
- `POST /v1/research/jobs/{job_id}:resume`
- `POST /v1/research/jobs/{job_id}:refine`
- `POST /v1/research/jobs/{job_id}:review`
- `GET /v1/research/jobs/{job_id}/bundle`
- `GET /v1/research/jobs/{job_id}/artifacts/{artifact_name}`
- `POST /v1/batch/research`

The HTTP response contract does not expose workspace paths. It returns stable artifact URLs keyed by public names.

## Artifact Delivery

Stable artifact names:

- `report.md`
- `report.html`
- `report_bundle.json`
- `claims.json`
- `sources.json`
- `audit_decision.json`
- `trace.jsonl`
- `manifest.json`
- `review_queue.json`
- `claim_graph.json`
- `review_actions.jsonl`

The API maps these names to the current local file layout, which lets future storage migrations preserve the surface contract.

## Review Semantics

Phase 4 adds a review endpoint and append-only review log:

- review actions are written to `audit/review_actions.jsonl`
- review actions are mirrored into runtime events
- if `trace.jsonl` already exists, a review event is appended there
- if `audit_decision.json` already exists, it is updated with the latest manual reviews

Phase 4 does not fully recompile `report_bundle.json` after manual review.

## Current Limits

- local API only
- no auth or tenant isolation
- no external queue
- no object storage indirection
- no full bundle recompilation after manual review

These are deliberate follow-on items for later phases, not hidden assumptions.
