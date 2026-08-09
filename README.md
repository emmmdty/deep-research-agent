# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://emmmdty.github.io/deep-research-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

**An evidence-first multi-agent deep research system.** It plans a research task into a task DAG,
runs parallel researcher and critic agents through governed model/tool gateways, audits every
critical claim against frozen evidence, and delivers an auditable report bundle — not a chat answer.

## Why This Project

Deep research (OpenAI Deep Research, Gemini Deep Research, Perplexity, STORM...) exploded in 2025.
This project asks a different question: *when the answer is wrong, can you prove it?*

- **Multi-agent, measured** — parallel researcher agents + a critic agent, orchestrated on a
  bounded DAG scheduler; the value of each component is proven by deterministic ablations, not
  asserted.
- **Evidence-first output** — the deliverable is a machine-readable report bundle where every
  critical claim carries an evidence span pointing into a frozen, immutable corpus manifest.
- **Industry-grade reliability** — checkpointed jobs that survive cancel/retry/resume/stale
  recovery; claim graphs, audit gates, and human review queues as first-class artifacts.

[Live demo](https://emmmdty.github.io/deep-research-agent/) · [Competitive landscape](./docs/final/COMPETITIVE_LANDSCAPE.md) · [Repository map](./docs/REPO_MAP.md)

### 60-Second Tour

1. **Overview** — what this system is: a research team that plans, researches in parallel,
   audits evidence, and delivers a report where every conclusion can be traced to its evidence.
2. **End-to-end demo** — watch one research task complete: planner spawns 3 parallel researchers
   (animated from the real trace journal), critic audits every claim, and the audited report is
   delivered with per-claim evidence panels.
3. **Reports** — browse the case library (demo case + real offline runs + eval fixture), each
   with claims, evidence excerpts, sources, and audit records.
4. **Benchmark** — direct answers to "is multi-agent worth it" backed by deterministic ablations,
   plus the sourced industry comparison.
5. **Architecture** — how it is implemented (task DAG, bounded scheduler, governed gateways,
   evidence store, product API).

## Architecture At A Glance

![Deep Research Agent user-facing architecture](./docs/assets/architecture-overview.png)

The canonical runtime is `src/deep_research_agent/`:

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Agent orchestration | `orchestration/` (`dag.py`, `scheduler.py`, `workers.py`, `reducer.py`) | Compile a research brief into an immutable task DAG; bounded asyncio scheduler runs ready tasks in parallel (up to 8 workers) with typed message passing |
| Agent roles | `ResearchPlanner` (researcher), critic tasks (`CriticDecision`) | Parallel researchers per objective; a critic audits dependencies and emits accepted/qualified/contradicted/unresolved decisions |
| Governance | `tool_gateway/`, `model_runtime/`, `policy/` | Role allow-lists, idempotency, caching, budget caps, retries; per-role model fallback chains with AES-GCM credentials |
| Evidence & audit | `auditor/`, `evidence_store/`, `corpus/` | Claim graph with support edges, conflict sets, review queues; frozen corpus manifests; provenance snapshots |
| Deliverable | `reporting/bundle_v2.py` | Deterministic reduction → audit → `report_bundle.json` (+ `report.md/html`) with sidecar artifacts |
| Reliability | `research_jobs/`, `observability/` | Checkpoints, events, leases, heartbeats, resume/retry/refine; credential-safe OpenTelemetry spans |
| Product surface | `gateway/`, `product/`, `apps/gui-web/` | CLI, local HTTP API (SSE event streams), authenticated multi-tenant product API on PostgreSQL, React workspace UI |

The canonical runtime is `src/deep_research_agent/` — the only implementation source of truth.
`legacy/` is the archived graph-first runtime with its full dependency closure (agents, workflows,
auditor, connectors, llm, policies, evaluation, research_policy). See [Repository Map](./docs/REPO_MAP.md).

## How A Research Job Runs

```
user topic → ResearchPlanner.plan() → ResearchDAG (research tasks ∥ critic task)
   → ResearchScheduler.run() [bounded asyncio, ≤8 workers, typed TaskSpec/WorkerOutput]
   → ToolGateway (governed retrieval) → ModelRegistry (role fallback chains)
   → EvidenceReducer.reduce() → EvidenceAuditor.audit()
   → ReportBundleCompilerV2.compile() → report_bundle.json + report.md/html
   → job artifacts under workspace/research_jobs/<job_id>/
```

Every critical claim in the bundle must resolve to an evidence span inside the frozen corpus
manifest; unverifiable claims are routed to a human review queue. The full lifecycle is documented
in [docs/architecture.md](./docs/architecture.md) and [docs/USER_GUIDE.md](./docs/USER_GUIDE.md).

## Evaluation & Benchmark Evidence

The release gate is deterministic and reproducible locally — no API keys, no network:

| Evidence | Where | Result |
| --- | --- | --- |
| Authoritative smoke gate | `evals/reports/phase5_local_smoke/` | 5 suites × smoke_local, all passed |
| Native regression | `evals/reports/native_regression/` | company12/industry12/trusted8/file8/recovery6 passed |
| Headline metrics | `evals/reports/followup_metrics/headline_metrics.json` | completion rate: `1.0`, critical claim support precision: `1.0`, citation error rate: `0.0`, policy compliance rate: `1.0` |
| Ablations (multi-agent value) | `evals/reports/followup_metrics/ablation_summary.md` | see table below |
| External benchmark adapters | `evals/external/` + `portfolio_summary.json` | BrowseComp/GAIA/LongBench-v2/LongFact/Facts grounding guarded smoke |
| Value scorecard | [docs/final/VALUE_SCORECARD.md](./docs/final/VALUE_SCORECARD.md) | full metric definitions and results |
| Experiment summary | [docs/final/EXPERIMENT_SUMMARY.md](./docs/final/EXPERIMENT_SUMMARY.md) | release smoke, native regression, external portfolio, follow-up metrics |

### Ablation Evidence: Why The Components Matter

Deterministic ablations prove each mechanism has a measurable causal effect:

| Ablation | Delta when removed |
| --- | --- |
| Audit gate (`audit_on_vs_off`) | unsupported claim leakage → 1.0 |
| Evidence-first synthesis (`evidence_first_vs_baseline`) | citation error rate → 1.0, provenance drops |
| Rerank/edge selection (`rerank_on_vs_off`) | critical claim support precision 1.0 → 0.5 |
| Strict source policy (`strict_source_policy_vs_relaxed`) | policy compliance 1.0 → 0.333 |

Run everything yourself:

```bash
uv sync --group dev
uv run python main.py eval run --suite company12 --variant smoke_local
uv run python main.py benchmark run --help
```

## Competitive Positioning

The 2025 deep research landscape is dominated by closed products (OpenAI, Gemini, Perplexity)
that deliver reports with post-hoc citations, and by open frameworks (STORM, LangChain
open_deep_research, smolagents) that omit audit trails. This project differentiates on
**auditability and governed evidence** — the same pain points Anthropic documents in its
multi-agent research system post (citation attribution, source quality, checkpoint/recovery).
See [docs/final/COMPETITIVE_LANDSCAPE.md](./docs/final/COMPETITIVE_LANDSCAPE.md) for the
evidence-backed comparison.

## Quick Start

```bash
uv sync --group dev
cp .env.example .env        # offline demo needs no secrets
uv run python main.py --help
```

Submit a job in deterministic offline mode (no API keys, no network; the scheduler
automatically switches the research profile to the rule-based benchmark pipeline):

```bash
SCHEDULER_RUNTIME_MODE=offline uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --json
```

Without the `SCHEDULER_RUNTIME_MODE=offline` prefix the CLI runs in production mode and
requires working LLM credentials in `.env`.

Local web demo (no Docker, file-backed SQLite, offline deterministic mode; the product
offline mode implies the offline scheduler):

```bash
PRODUCT_DATABASE_URL=sqlite+pysqlite:///./workspace/product.db \
PRODUCT_OFFLINE_MODE=true \
uv run uvicorn deep_research_agent.gateway.api:app --reload
# separate terminal
npm run dev --prefix apps/gui-web    # open http://127.0.0.1:5173
```

Full Compose profile (PostgreSQL/pgvector + MinIO + GROBID + Phoenix) with the credential-free
offline scheduler:

```bash
docker compose up --build     # open http://127.0.0.1:8000
```

Live scholarly research requires an explicit `SCHEDULER_FACTORY_PATH`; the runtime never silently
falls back from production to offline execution.

## Artifact Contract

Completed jobs write `workspace/research_jobs/<job_id>/`:

- `report_bundle.json` — authoritative machine-readable output
- `report.md`, `report.html` — reader-facing renderings
- `claims.json`, `sources.json`, `audit_decision.json`, `review_queue.json`, `claim_graph.json` — audit sidecars
- `trace.jsonl`, `manifest.json`, `review_actions.jsonl` — execution and review records

```bash
uv run python main.py bundle --job-id <job_id> --json
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
```

## Repository Layout

```text
src/deep_research_agent/  canonical runtime (orchestration, auditor, reporting, product...)
apps/gui-web/             React product workspace (topics, runs, reports, memory, admin)
apps/demo-site/           static GitHub Pages demo (ask a question, watch it researched)
configs/                  runtime and source-profile config
evals/                    deterministic eval assets, reports, and fixtures
docs/                     reviewer docs (index, architecture, benchmarks, final)
tests/                    regression tests
scripts/                  smoke, eval, demo-data, and diagnostic commands
migrations/               product database migrations
deploy/                   deployment fragments (nginx, GROBID notes)
legacy/                   archived graph-first runtime (orchestrator-v1 compatibility path)
```

## Current Limits

- Deployment profile is a small-team Compose stack, not a horizontally scaled SaaS control plane.
- Deterministic eval is authoritative; live-provider quality/cost comparisons are roadmap items.
- Open-web search is discovery-only; critical claims are limited to governed, frozen sources.
- Memory is explicit CRUD plus subject-scoped recall; conversation-to-memory promotion is roadmap.

## Roadmap

- Measure and harden queue/object-storage adapters after the Postgres/MinIO profile is exercised.
- Live-provider head-to-head comparisons (ours vs open_deep_research vs gpt-researcher) with cost
  and quality telemetry.
- Expand GAIA/BrowseComp guarded subset coverage; review integrity findings before scaling.
- Human-in-the-loop review flows that recompile or annotate delivered bundles.

## License

MIT. See [LICENSE](./LICENSE).
