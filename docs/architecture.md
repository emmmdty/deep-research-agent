# Deep Research Agent Architecture

This document describes the current V2 product architecture and its deployment boundary.

## System Boundary

The supported system is a tenant-aware, evidence-first research product with these surfaces:

- React research workspace and admin views
- authenticated FastAPI product API
- durable multi-agent scheduler and reconnectable SSE events
- scholarly corpus, parser fallback, shared public cache, and scoped memory
- deterministic evaluation and release manifests

The V2 product uses PostgreSQL/pgvector as its production source of truth and MinIO-compatible
object storage for immutable artifacts. SQLite and in-memory adapters are explicit offline/test
adapters only. All supported surfaces share the typed runtime kernel:

- `ResearchBrief`, `TaskSpec`, `EvidencePacket`, and `ReportBundleV2`
- `ResearchPlanner` and the bounded asyncio scheduler (at most eight active workers)
- governed model/tool gateways with a frozen config snapshot per run
- tenant-scoped corpus, memories, runs, events, and report artifacts

The eval and release-smoke surfaces reuse the same runtime and artifact contracts, then aggregate claim-centric evidence into suite summaries and release-gate manifests.

The old serial `ResearchJobService` and legacy `/v1/research/jobs` surface remain read-compatible
for historical artifacts. They are compatibility-only and are not the V2 product boundary.

## Canonical Flow

```text
conversation message
  -> intent and cost gate
  -> structured research brief
  -> frozen tenant config + corpus manifest
  -> dynamic task DAG (researcher / retriever / critic / compiler)
  -> governed tools and model endpoints
  -> deterministic evidence reduction and semantic audit
  -> immutable report bundle + source/evidence graph
  -> reconnectable events and evidence-first workspace
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

Owns compatibility storage and the worker bridge used by the V2 runtime:

- job records
- event log
- checkpoints
- worker lease and heartbeat
- cancel / retry / resume / refine
- stale recovery
- legacy orchestrator stage execution

### `src/deep_research_agent/kernel/`, `orchestration/`, and `reporting/`

Own the V2 contracts and execution path:

- typed task DAG, checkpoints, cancellation, branch-only retries, and monotonic events
- deterministic merge and evidence audit; unsupported critical claims cannot enter summaries
- versioned `ReportBundleV2` with exact source-version and evidence-span locators

### `src/deep_research_agent/product/`, `corpus/`, and `memory_v2/`

Own product persistence and user boundaries:

- Argon2id invite-only authentication, same-site sessions, CSRF, and tenant checks
- PostgreSQL repositories for topics, conversations, runs, events, corpus grants, and memories
- GROBID primary parsing with Docling fallback; public cache keyed by content and parser version
- run-state TTL, conversation focus TTL, and explicit sensitive-memory confirmation

### `src/deep_research_agent/observability/` and `src/deep_research_agent/evals/`

Own release evidence:

- OpenTelemetry spans contain identifiers and aggregate usage only; prompts, documents, and secrets
  are never exported
- framework bake-off, 1/2/4/8-worker scaling, and corpus acceptance thresholds run offline without
  provider credentials; live adapters are explicit and never silently substituted

### `src/deep_research_agent/connectors/`

Owns the document ingestion boundary:

- connector registry
- search / fetch / file-ingest contracts
- snapshot persistence
- URI safety checks
- legacy tool adapters

### `src/deep_research_agent/policy/` and `configs/source_profiles/`

Owns source governance:

- source profiles
- allow / deny domain rules
- fetch budgets
- policy overrides

The root `policies/` package is a compatibility shim for older imports and tests. It is not the
canonical source-governance implementation.

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

### `src/deep_research_agent/evals/`

Owns the canonical Phase 5 local eval stack:

- suite definitions and threshold loading
- deterministic fixture execution over the rebuilt runtime
- company / industry / trusted / file / recovery suite summaries
- saved bundle-aware metrics and suite manifests

### `evals/`

Owns the filesystem contract for evaluation assets:

- `evals/suites/` for suite config and thresholds
- `evals/datasets/` for frozen smoke fixtures
- `evals/rubrics/` for rubric metadata
- `evals/reports/` for committed low-cost outputs and release manifests
- `evals/legacy_diagnostics/` for the older benchmark narrative

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
- `eval run`

### HTTP API

V2 product endpoints include:

- `POST /v1/auth/login`, `POST /v1/auth/logout`, and invitation acceptance
- `POST /v1/topics`, `GET /v1/topics/{id}`, and topic-scoped conversations
- `POST /v1/conversations/{id}/messages` returning `direct_answer`,
  `clarification_required`, or `research_job_started`
- `GET/POST /v1/topics/{topic_id}/runs`, run status/cancel/resume/bundle, and reconnectable SSE
- private corpus upload/search and scoped memory CRUD/export
- administrator-only model, tool, and frozen runtime-config endpoints

The legacy compatibility endpoints remain available for historical local jobs:

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

### Eval and Release Manifests

V2 adds saved deterministic suite outputs:

- `evals/reports/phase5_local_smoke/<suite>/summary.json`
- `evals/reports/phase5_local_smoke/<suite>/RESULTS.md`
- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/reports/phase5_local_smoke/RESULTS.md`

The release gate now consumes claim-centric suite evidence in addition to runtime/security/docs/API diagnostics.

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
- heavy benchmark/comparator tooling remains as diagnostics and historical comparison, not the primary release contract

These are deliberate follow-on items for later phases, not hidden assumptions.

## Deployment And Operations

`docker compose up --build` starts API, Web, recovery worker, PostgreSQL/pgvector, MinIO, GROBID,
and Phoenix. The Web container is an unprivileged Nginx reverse proxy and publishes the single
same-origin demo URL `http://127.0.0.1:8000`; it proxies `/v1/` to the internal API. PostgreSQL,
MinIO, and Phoenix data use named persistent volumes. API startup validates the master key,
bootstrap admin, and scheduler mode, then runs `alembic upgrade head` before serving traffic.

Production mode requires `SCHEDULER_FACTORY_PATH` to resolve a real provider-neutral scheduler
factory. The only credential-free mode is the explicit `SCHEDULER_RUNTIME_MODE=offline` demo mode.
Missing production secrets or a missing factory fail closed.

## Supported Questions And Source Limits

The first domain pack is event graphs, agents, and LLMs. A user can ask for a source-grounded
state-of-the-field report, compare methods or papers, trace a claim to exact evidence, inspect
contradictions, or request an explicit corpus refresh. Ambiguous or high-cost requests trigger a
clarification brief before any worker starts.

The product does not promise unrestricted current-web coverage. Critical claims require frozen
document versions and exact spans from governed sources. The initial reliable corpus is scholarly
metadata/full text from arXiv, ACL Anthology, OpenAlex, Crossref, DataCite, DBLP, PMLR, NeurIPS,
and licensed user uploads; arbitrary web search is discovery-only and cannot support critical
claims. Source outages produce freshness warnings, not fabricated or silently stale conclusions.
