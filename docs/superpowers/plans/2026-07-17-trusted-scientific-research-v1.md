# Trusted Scientific Research Agent V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the serial local demo with a domain-agnostic, evidence-first multi-agent research product whose first production domain studies how event graphs, agents, and LLMs interact.

**Architecture:** A typed research kernel compiles conversational briefs into durable task DAGs, executes at most eight independent workers through governed model and tool gateways, reduces their evidence deterministically, and publishes a versioned report bundle. PostgreSQL/pgvector is the production source of truth, MinIO stores immutable artifacts, and the React workspace exposes research progress and evidence without exposing chain-of-thought. SQLite and in-memory adapters remain available only for tests and offline development.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, asyncio, SQLAlchemy 2, PostgreSQL/pgvector, MinIO/S3, OpenAI-compatible model APIs, React 19, TypeScript, Vite, TanStack Query, React Router, Cytoscape.js, Markdown, Docker Compose, OpenTelemetry/Phoenix.

## Global Constraints

- `03-deep-research-agent` is the only canonical repository; do not modify `03-deep-research-agent-product-v1`.
- Preserve the user's original dirty main worktree. Implement only on `feat/trusted-research-v1` in the isolated worktree.
- The runtime must be domain-agnostic. Event graph x Agent x LLM behavior belongs only in a versioned `DomainPack`.
- Maximum active research workers per job is 8 in V1; the contract must accept a configurable limit without an API change.
- Agents exchange typed task, evidence, and artifact references; never use free-form agent chat as the system of record.
- Every critical report claim must resolve to an immutable document version and exact evidence span. Unsupported critical claims cannot enter the executive summary.
- OpenAI-compatible endpoint URL, model, and credential are independently configurable per role. Running jobs freeze a config version and fallback chain.
- Show task status, role, model, retries, source count, and timing in the Web UI; never expose hidden reasoning, system prompts, or full internal agent conversations.
- Public-document cache is shared by content hash. User uploads, permissions, conversations, and memories are tenant-isolated.
- Job scratchpad TTL is 7 days, conversation focus is 30 days, raw conversation retention is 90 days, and confirmed preferences/topics persist until deletion or archive.
- Default follow-up behavior answers from the frozen snapshot and displays its cutoff; a refresh is explicit or triggered by stale/out-of-scope evidence.
- Use TDD for production behavior. No local GPU work. All new Python APIs require type hints and Pydantic validation at boundaries.

---

### Task 1: Research Kernel Contracts And Domain Packs

**Files:**
- Create: `src/deep_research_agent/kernel/contracts.py`
- Create: `src/deep_research_agent/domain_packs/{models.py,registry.py}`
- Create: `configs/domain_packs/event-graph-agents-llms.yaml`
- Create: `configs/domain_packs/software-supply-chain-smoke.yaml`
- Create: `tests/test_kernel_contracts.py`
- Modify: `docs/REPO_MAP.md`

**Interfaces:**
- Produce `ResearchBrief`, `TaskSpec`, `TaskResult`, `ArtifactRef`, `EvidenceSpan`, `EvidencePacket`, `ClaimRecord`, `ResearchGraphNode`, `ResearchGraphEdge`, `CorpusManifest`, and `ReportBundleV2` Pydantic models.
- Produce `DomainPackRegistry.load(pack_id: str) -> DomainPack` and `DomainPackRegistry.list() -> list[DomainPackSummary]`.
- `TaskSpec` carries `task_id`, `job_id`, `kind`, `role`, `objective`, `depends_on`, `input_artifacts`, `output_schema`, `budget`, and `idempotency_key`.
- `ReportBundleV2` carries report Markdown, accepted/qualified claims, evidence matrix, generic research graph, sources, audit summary, corpus manifest, and run manifest.

- [ ] Add failing tests proving both packs load, their schemas validate, the smoke pack contains no event-graph vocabulary, invalid dependencies are rejected, critical accepted claims require evidence, and `ReportBundleV2.schema_version == "2.0"`.
- [ ] Run `uv run pytest -q tests/test_kernel_contracts.py` and confirm failure because the kernel/domain-pack modules do not exist.
- [ ] Implement the minimal typed models and YAML registry. Keep domain relations declarative and reject unknown top-level fields.
- [ ] Copy the already-reviewed `apps/` rows from the user's dirty `docs/REPO_MAP.md` into the isolated worktree so the pre-existing repository-standard test passes.
- [ ] Run `uv run pytest -q tests/test_kernel_contracts.py tests/test_public_repo_standards.py` and `uv run ruff check .`.
- [ ] Commit as `feat: add research kernel and domain packs`.

### Task 2: Versioned Model Registry And Governed Tool Gateway

**Files:**
- Create: `src/deep_research_agent/model_runtime/{models.py,registry.py,client.py}`
- Create: `src/deep_research_agent/tool_gateway/{models.py,gateway.py,registry.py}`
- Create: `tests/test_model_runtime.py`
- Create: `tests/test_tool_gateway.py`
- Modify: `pyproject.toml`, `uv.lock`

**Interfaces:**
- Produce `ModelEndpoint`, `AgentRoleProfile`, `RuntimeConfigVersion`, `ModelCapabilityReport`, and write-only `EndpointCredentialInput`.
- Produce `ModelRegistry.activate(version_id)`, `snapshot_for_job(job_id)`, `resolve(role, attempt)`, and `probe(endpoint_id)`; snapshots are immutable and fallback resolution records the actual endpoint/model.
- Produce `ToolSpec`, `ToolInvocation`, `ToolResultEnvelope`, and `ToolGateway.invoke(task, call, context)` with allowlists, tenant checks, timeout, retry, budget, cache, and idempotency enforcement.
- Credential persistence uses AES-GCM with a 32-byte environment master key; serializers never return plaintext credentials.

- [ ] Add failing tests for per-role endpoint selection, immutable snapshots, same-tier fallback, failed capability probes, secret redaction, role/tool denial, tenant denial, cache hits, and duplicate idempotency keys.
- [ ] Run the two focused test files and confirm missing-module failures.
- [ ] Add only the required dependencies: `cryptography`, `pydantic-ai-slim[openai]`, and test-time HTTP support. Regenerate the uv lock.
- [ ] Implement registry storage protocols with in-memory adapters for tests and production-facing interfaces for Task 5.
- [ ] Implement the OpenAI-compatible client factory using independent base URL, model, key, timeout, structured-output, and tool-use capabilities per endpoint.
- [ ] Implement the gateway. Treat tool output as untrusted data and return artifact references for large results.
- [ ] Run focused tests, `uv run ruff check .`, and commit as `feat: add model registry and tool gateway`.

### Task 3: Dynamic Multi-Agent DAG, Evidence Audit, And Bundle Compiler

**Files:**
- Create: `src/deep_research_agent/orchestration/{dag.py,scheduler.py,workers.py,reducer.py,events.py}`
- Create: `src/deep_research_agent/auditor/semantic.py`
- Create: `src/deep_research_agent/reporting/bundle_v2.py`
- Create: `tests/test_multi_agent_runtime.py`
- Create: `tests/test_report_bundle_v2.py`
- Modify: `src/deep_research_agent/research_jobs/orchestrator.py`

**Interfaces:**
- Produce `ResearchPlanner.plan(brief, domain_pack) -> ResearchDAG`, `ResearchScheduler.run(job, dag, config_snapshot) -> RunResult`, and `EvidenceReducer.reduce(packets) -> ReducedEvidence`.
- Scheduler supports dynamic fan-out, dependency readiness, maximum 8 active workers, cancellation, branch-only retry, event sequence IDs, and task checkpoints.
- Worker outputs always validate against the declared output schema. Deterministic merge owns document/claim deduplication; an explicit critic task owns semantic disagreements.
- `EvidenceAuditor.audit(claims, corpus_manifest)` classifies accepted, qualified, contradicted, or unsupported and prevents unsupported critical claims from entering the executive summary.

- [ ] Add failing async tests with deterministic fake workers for 1/4/8 concurrency, dependency ordering, max-worker enforcement, cancellation, retry of only the failed branch, event ordering, schema rejection, and no duplicate idempotent tool side effects.
- [ ] Add failing bundle tests for exact evidence locators, contradictory claims, generic graph edge provenance, audit degradation, and deterministic regeneration from a frozen manifest.
- [ ] Run focused tests and confirm failures before runtime changes.
- [ ] Implement the framework-independent DAG and asyncio scheduler first; wrap model calls through the Task 2 interfaces rather than importing a provider SDK in orchestration.
- [ ] Bridge the canonical `ResearchJobService` to the new scheduler while retaining legacy artifact reads for old bundles.
- [ ] Implement semantic audit hooks with deterministic evidence requirements; LLM judging is optional enrichment and never the only acceptance signal.
- [ ] Run focused runtime/auditor/report tests plus existing job/auditor regressions, then commit as `feat: add durable multi-agent research runtime`.

### Task 4: Corpus, Parsing, Shared Cache, And Tenant-Isolated Memory

**Files:**
- Create: `src/deep_research_agent/corpus/{models.py,service.py,parsers.py,storage.py}`
- Create: `src/deep_research_agent/memory_v2/{models.py,service.py,policy.py}`
- Create: `tests/test_corpus_service.py`
- Create: `tests/test_memory_v2.py`
- Modify: `src/deep_research_agent/connectors/registry.py`

**Interfaces:**
- Produce `WorkRecord`, `DocumentVersion`, `SourceDescriptor`, `CorpusSnapshot`, and `CorpusService.ingest/search/freeze_manifest`.
- Public cache keys are `sha256 + parser_name + parser_version`; authorization lives in separate tenant/document grants. A private upload can never become public through hash deduplication.
- Define `ScholarlyParser` protocol with `GrobidParser` primary and `DoclingParser` fallback adapters; external services remain optional in unit tests.
- Produce memory scopes `run_state`, `conversation_focus`, `user_memory`, `topic_memory`, `agent_experience`; memory records include provenance, confidence, sensitivity, expiry, status, and supersession.

- [ ] Add failing tests for public cache reuse, private isolation, version preservation, license/storage-policy enforcement, parser fallback, frozen manifests, memory TTLs, sensitive-write confirmation, conflict supersession, user delete/export, and cross-tenant search denial.
- [ ] Run focused tests and confirm missing behavior.
- [ ] Implement in-memory repositories and service behavior; define SQL repository protocols for Task 5.
- [ ] Wire approved scholarly connectors through typed corpus records; arbitrary-web connector remains discovery-only and cannot support critical claims.
- [ ] Run focused tests plus connector regressions and commit as `feat: add corpus and governed memory services`.

### Task 5: PostgreSQL Product Context, Auth, APIs, And Reconnectable Events

**Files:**
- Create: `src/deep_research_agent/product/{db.py,tables.py,repositories.py,auth.py,service.py}`
- Create: `src/deep_research_agent/gateway/routes/{auth.py,chat.py,topics.py,runs.py,corpus.py,memory.py,admin.py}`
- Create: `tests/test_product_api_v2.py`
- Create: `tests/test_event_stream.py`
- Modify: `src/deep_research_agent/gateway/api.py`
- Modify: `pyproject.toml`, `uv.lock`

**Interfaces:**
- Add invite-only users with `user` and `admin` roles, Argon2id password hashing, HttpOnly same-site sessions, CSRF protection, and tenant-scoped repositories.
- `POST /v1/conversations/{id}/messages` returns exactly one of `direct_answer`, `clarification_required`, or `research_job_started` plus a structured brief.
- Add topic workspace, run create/status/cancel/resume/bundle, private corpus upload, memory CRUD/export, and admin model/tool/config endpoints.
- `GET /v1/runs/{id}/events` is SSE with monotonic IDs, heartbeat, `Last-Event-ID` resume, and deduplication.
- Production database URL must be PostgreSQL; SQLite is accepted only under explicit test/offline mode.

- [ ] Add failing API tests for invitations, login/logout, role checks, CSRF, tenant isolation, simple-message direct answers, ambiguous/high-cost clarification, snapshot quick answers, explicit refresh, model secret redaction, and running-job config freeze.
- [ ] Add failing SSE tests for ordered delivery, reconnect from event ID, heartbeat, terminal completion, and cross-tenant denial.
- [ ] Add SQLAlchemy, Alembic, psycopg, pgvector, argon2, and multipart dependencies; regenerate the lock.
- [ ] Implement repository-backed services and route modules. Use SQLite in tests through the explicit offline adapter, not as the production default.
- [ ] Keep old `/v1/research/jobs` reads functional for legacy artifacts while new product writes use run/topic APIs.
- [ ] Run focused API tests and the existing gateway/CLI suite, then commit as `feat: add multi-user research product api`.

### Task 6: Research Workspace And Admin Web Application

**Files:**
- Create: `apps/gui-web/src/{router.tsx,types.ts}`
- Create: `apps/gui-web/src/features/{workspace,report,evidence,graph,runs,memory,admin}/`
- Create: `apps/gui-web/src/components/`
- Create: `apps/gui-web/src/workspace.test.tsx`
- Modify: `apps/gui-web/src/App.tsx`, `api/client.ts`, `styles.css`, `package.json`, `package-lock.json`

**Design Contract:**
- Palette: paper white `#F7F8F6`, ink `#18201D`, graphite `#5D6762`, evidence teal `#087E6D`, warning amber `#B76412`, contradiction red `#B23A3A`.
- Type: system/UI body stack, a restrained editorial serif only for report titles, and tabular monospace for evidence locators and run telemetry. Letter spacing is `0`.
- Layout: narrow topic rail, conversation/activity column, full report canvas, and contextual evidence drawer. On mobile these become routes/drawers rather than overlapping columns.
- Signature: a vertical evidence spine beside the report; selecting a claim connects it to source spans and graph relations without decorative cards.

**Interfaces:**
- Routes: `/topics`, `/topics/:topicId`, `/topics/:topicId/runs/:runId`, `/memory`, `/admin/models`, `/admin/runtime`.
- Workspace views: Report, Changes, Evidence, Relationship graph, Papers, Runs. Worker display includes task, role, model, state, retry, source count, elapsed time; no reasoning text.

- [ ] Add failing component tests for simple prompt submission, clarification brief editing, refresh, SSE reconnect, report Markdown rendering, citation-to-evidence drawer, graph evidence selection, memory deletion, admin secret redaction, and mobile navigation.
- [ ] Run `npm test` and confirm expected failures.
- [ ] Add React Router, TanStack Query, `react-markdown`, Cytoscape.js wrapper, and Lucide React; update the lock without using unsafe automatic audit fixes.
- [ ] Implement feature modules and API hooks. Replace raw `<pre>` reports with accessible semantic Markdown and a stable reading layout.
- [ ] Implement responsive CSS, visible focus, reduced motion, loading/empty/error states, and stable dimensions for tabs, task rows, graph, and evidence drawer.
- [ ] Run `npm test`, `npm run lint`, and `npm run build`; commit as `feat: build scientific research workspace`.

### Task 7: Deployment, Observability, Evaluation, And Cutover Documentation

**Files:**
- Create: `docker-compose.yml`, `Dockerfile`, `deploy/grobid/README.md`
- Create: `src/deep_research_agent/observability/tracing.py`
- Create: `src/deep_research_agent/evals/{framework_bakeoff.py,agent_scaling.py,product_acceptance.py}`
- Create: `tests/test_framework_bakeoff.py`, `tests/test_product_acceptance.py`
- Modify: `docs/architecture.md`, `README.md`, `README.zh-CN.md`, `.env.example`

**Interfaces:**
- Compose services: API, Web, worker, PostgreSQL/pgvector, MinIO, GROBID, Phoenix. Redis is absent unless measured evidence demonstrates a need.
- OpenTelemetry spans record job/task IDs, role, endpoint/model, tool, latency, token/cost, retry, and artifact IDs without credentials or private document content.
- Framework bake-off has adapters for PydanticAI+DBOS, LangGraph, and Google ADK; hard gates are duplicate-side-effect prevention, branch-only recovery, per-role endpoints, config snapshot, structured artifacts, cancel, and resume. If all pass and performance is within 10%, select PydanticAI+DBOS.
- Agent scaling reports quality, elapsed time, token use, tool calls, and errors for 1/2/4/8 workers over the same frozen inputs.

- [ ] Add failing tests for Compose service/config contracts, trace redaction, deterministic framework scoring/selection, acceptance threshold evaluation, and agent-scaling result schemas.
- [ ] Run focused tests and confirm failures.
- [ ] Implement Compose health checks, non-root containers, persistent volumes, environment validation, migration startup, and CPU-safe parser configuration.
- [ ] Implement OpenTelemetry integration with Phoenix OTLP export optional by environment.
- [ ] Implement deterministic/offline bake-off and scaling harnesses plus optional live-model execution; never require provider credentials for unit tests.
- [ ] Update architecture and runbooks to make V2 the canonical product, mark the old serial runtime compatibility-only, and document supported user questions and source limitations.
- [ ] Run all Python tests, Ruff, all Web tests/lint/build, Docker Compose config validation, CLI help, and targeted API smoke.
- [ ] Commit as `feat: ship trusted scientific research v1`.

### Task 8: Whole-Branch Review And Release Evidence

**Files:**
- Create: `docs/reports/trusted-scientific-research-v1-verification.md` only if `docs/reports/` is intended to remain tracked; otherwise keep verification output in the task report.
- Modify only files required by final review findings.

- [ ] Generate a full review package from the branch merge base and dispatch the final code reviewer.
- [ ] Fix every Critical and Important finding with focused failing tests first, then re-run the reviewer.
- [ ] Run the complete verification suite fresh and record exact commands, counts, and known external-service skips.
- [ ] Inspect desktop and mobile Playwright screenshots and verify report, graph, and evidence drawer have no overlap or blank states.
- [ ] Start the local development server on available ports and report the URL, without exposing credentials.
- [ ] Use the finishing-a-development-branch workflow; do not merge, push, or delete the branch without the user's final choice.
