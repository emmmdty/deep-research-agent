# Deep Research Agent Architecture

This document describes the current V2 product architecture and its deployment boundary.

## System Boundary

The supported system is a tenant-aware, evidence-first research product with these surfaces:

- React research workspace and admin views
- authenticated FastAPI product API
- durable multi-agent scheduler and reconnectable SSE events
- tenant-upload corpus freezing, reusable scholarly corpus/parser services, and scoped memory
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

### `src/deep_research_agent/agents/`

Own the model-driven agent roles (planner / researcher / critic):

- `planner.py` — model decomposes the brief into sub-objectives with a deterministic
  fallback; a **required-objective coverage check** appends deterministic tasks for any
  requested objective the model missed (character-bigram fuzzy match on objectives)
- `researcher.py` — a native **function-calling agentic loop**: `plan_queries()` proposes
  queries with a per-query tool choice; the governed tool gateway executes them;
  `assess_coverage()` reflects on whether the evidence answers the objective and issues
  follow-up queries for uncovered gaps; `select_pages()` picks URLs whose full content the
  `fetch_page` tool then reads and chunks; `submit_claims()` returns schema-constrained
  claims where every quote must be verbatim in its source (longest-verbatim-span matcher,
  otherwise the claim is dropped). Chat clients without function-calling support degrade
  to prompt-based JSON extraction
- `critic.py` — contradiction review over grounded evidence spans, then report synthesis
- `llm.py` — OpenAI-compatible client with native `tools` API support (multi-turn parallel
  tool loop), prompt-based JSON extraction, budget-widening and direct-answer retries for
  thinking models, and an optional `LLM_DISABLE_THINKING` extra-body switch for providers
  whose reasoning mode burns the whole output budget

### `src/deep_research_agent/product/`, `corpus/`, and `memory_v2/`

Own product persistence and user boundaries:

- Argon2id invite-only authentication, same-site sessions, CSRF, and tenant checks
- PostgreSQL repositories for topics, conversations, runs, events, tenant uploads, and memories
- run-owned copies and hash manifests for selected private uploads before worker start
- product memory provenance, TTL cleanup, conflict supersession, recall into research briefs, and
  explicit sensitive-memory confirmation
- the current product contract is explicit memory CRUD plus subject-scoped recall; automatic
  conversation-to-long-term promotion is intentionally deferred
- reusable GROBID/Docling and shared-cache services; a production scheduler must compose these into
  live public-source retrieval

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

The archived `legacy/policies/` package is retained for the graph-first runtime only. It is not
the canonical source-governance implementation.

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
- private corpus upload/list/get and scoped memory CRUD/export
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

- the bundled offline scheduler exercises the product workflow but performs no external retrieval
- live research requires an explicitly configured external `SCHEDULER_FACTORY_PATH`
- the connector substrate currently includes arXiv, GitHub, open-web, and local files; ACL
  Anthology, OpenAlex, Crossref, DataCite, DBLP, PMLR, and NeurIPS are source-design targets
- no external queue; worker recovery remains job-local
- no full bundle recompilation after manual review
- heavy benchmark/comparator tooling remains diagnostic, not the primary release contract

These are deliberate follow-on items for later phases, not hidden assumptions.

## Deployment And Operations

`docker compose up --build` starts API, Web, recovery worker, PostgreSQL/pgvector, MinIO, GROBID,
and Phoenix. The Web container is an unprivileged Nginx reverse proxy and publishes the single
same-origin demo URL `http://127.0.0.1:8000`; it proxies `/v1/` to the internal API. PostgreSQL,
MinIO, and Phoenix data use named persistent volumes. API startup validates the master key,
bootstrap admin, and scheduler mode, then runs `alembic upgrade head` before serving traffic.

Production mode requires `SCHEDULER_FACTORY_PATH` to resolve a real provider-neutral scheduler
factory. The only credential-free mode is the explicit `SCHEDULER_RUNTIME_MODE=offline` demo mode.
Missing production secrets or a missing factory fail closed. Offline reports state that no
evidence-backed conclusion was produced rather than fabricating a result.

## Supported Questions And Source Limits

The first domain pack is event graphs, agents, and LLMs. A user can ask for a source-grounded
state-of-the-field report, compare methods or papers, trace a claim to exact evidence, inspect
contradictions, or request an explicit corpus refresh. Ambiguous or high-cost requests trigger a
clarification brief before any worker starts.

The product does not promise unrestricted current-web coverage. Critical claims require frozen
document versions and exact spans from governed sources. Today, the product API freezes selected
tenant uploads and makes their paths and hashes available to the scheduler. The bundled connector
substrate includes arXiv, GitHub, open-web, and local files, but only an explicitly configured
production scheduler performs live retrieval. ACL Anthology, OpenAlex, Crossref, DataCite, DBLP,
PMLR, and NeurIPS are documented source-design targets and are not yet product connectors.
Arbitrary web search remains discovery-only and cannot support critical claims.
