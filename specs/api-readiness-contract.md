# API And Batch Contract

Status: implemented in Phase 4

This file keeps its historical path for link stability. Its content now describes the implemented local HTTP API and batch surface.

## Scope

The supported server surface is a local FastAPI wrapper over the deterministic job runtime:

- same `ResearchJobService`
- same SQLite + filesystem workspace
- same append-only job events and checkpoint flow
- same report bundle and audit sidecars

It is not a multi-tenant SaaS boundary, not an authenticated production control plane, and not a replacement for future server-grade queue/storage work.

## HTTP Endpoints

### Jobs

- `POST /v1/research/jobs`
- `GET /v1/research/jobs/{job_id}`
- `GET /v1/research/jobs/{job_id}/events`
- `POST /v1/research/jobs/{job_id}:cancel`
- `POST /v1/research/jobs/{job_id}:retry`
- `POST /v1/research/jobs/{job_id}:resume`
- `POST /v1/research/jobs/{job_id}:refine`
- `POST /v1/research/jobs/{job_id}:review`

### Artifacts

- `GET /v1/research/jobs/{job_id}/bundle`
- `GET /v1/research/jobs/{job_id}/artifacts/{artifact_name}`

Supported artifact names:

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

### Batch

- `POST /v1/batch/research`

`POST /v1/batch/research` is submit-many only in Phase 4. It validates the same per-job request contract as `POST /v1/research/jobs` and returns the accepted jobs immediately.

## Request Contract

### Submit job

```json
{
  "topic": "Anthropic company profile",
  "max_loops": 2,
  "research_profile": "default",
  "source_profile": "company_trusted",
  "allow_domains": ["anthropic.com"],
  "deny_domains": ["reddit.com"],
  "connector_budget": {
    "max_fetches_per_task": 2
  },
  "start_worker": false
}
```

### Refine job

```json
{
  "instruction": "Expand the competitor comparison table.",
  "start_worker": false
}
```

### Review job

```json
{
  "review_item_id": "review-1",
  "claim_id": "claim-1",
  "decision": "override",
  "reason": "Human reviewer accepted the claim after manual verification.",
  "reviewer": "alice"
}
```

### Batch submit

```json
{
  "jobs": [
    {
      "topic": "Anthropic company profile",
      "max_loops": 1,
      "research_profile": "default",
      "start_worker": false
    },
    {
      "topic": "AI coding agent market map",
      "max_loops": 2,
      "research_profile": "benchmark",
      "source_profile": "industry_broad",
      "start_worker": false
    }
  ]
}
```

## Response Contract

The public job response intentionally does not expose local filesystem paths as stable IDs. Instead it returns stable API URLs:

- `self`
- `events`
- `bundle`
- `report_markdown`
- `report_html`
- `report_bundle`
- `claims`
- `sources`
- `audit_decision`
- `trace`
- `manifest`
- `review_queue`
- `claim_graph`
- `review_actions`

Representative response:

```json
{
  "job_id": "20260421T000000Z-abc12345",
  "topic": "Anthropic company profile",
  "status": "created",
  "current_stage": "clarifying",
  "created_at": "2026-04-21T00:00:00+00:00",
  "updated_at": "2026-04-21T00:00:00+00:00",
  "attempt_index": 1,
  "retry_of": null,
  "cancel_requested": false,
  "source_profile": "company_trusted",
  "budget": {},
  "policy_overrides": {
    "allow_domains": ["anthropic.com"],
    "deny_domains": ["reddit.com"],
    "budget": {
      "max_fetches_per_task": 2
    }
  },
  "connector_health": {},
  "audit_gate_status": "unchecked",
  "critical_claim_count": 0,
  "blocked_critical_claim_count": 0,
  "error": null,
  "artifact_urls": {
    "self": "/v1/research/jobs/20260421T000000Z-abc12345",
    "events": "/v1/research/jobs/20260421T000000Z-abc12345/events",
    "bundle": "/v1/research/jobs/20260421T000000Z-abc12345/bundle"
  }
}
```

## Semantic Guarantees

- Lifecycle semantics stay job-oriented and deterministic.
- `status` and `audit_gate_status` remain separate contracts.
- `cancel`, `retry`, `resume`, and `refine` still reuse the canonical runtime methods.
- Events remain append-only and ordered by `sequence`.
- Bundle retrieval returns `report_bundle.json`, not a prose-only surface.
- Artifact routes hide local paths behind stable names.
- Review writes are append-only and recorded as runtime events.

## Known Limits In Phase 4

- No auth or tenant boundary
- No external queue or worker pool
- No object storage indirection
- No server-side pagination beyond `after_sequence` for events
- Review writes update runtime state and review sidecars, but do not rewrite the entire report bundle JSON
