# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://emmmdty.github.io/deep-research-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

**An evidence-first multi-agent deep research system.** A model-driven planner
decomposes a research question into a task DAG; parallel researcher agents run
real-time governed web/GitHub/arXiv search and extract only claims they can
ground in frozen evidence; a critic agent audits every critical claim and
synthesizes an auditable report bundle — not a chat answer.

## Why This Project

Deep research (OpenAI Deep Research, Gemini Deep Research, Perplexity, STORM...) exploded in 2025.
This project asks a different question: *when the answer is wrong, can you prove it?*

- **Multi-agent, measured** — a real LLM planner, parallel LLM researcher agents,
  and an LLM critic are orchestrated on a bounded DAG scheduler; the value of each
  component is proven by deterministic ablations, not asserted, and live runs are
  captured as committed evidence.
- **Evidence-first output** — the deliverable is a machine-readable report bundle where every
  critical claim carries an evidence span pointing into a frozen, immutable corpus manifest.
- **Industry-grade reliability** — checkpointed jobs that survive cancel/retry/resume/stale
  recovery; claim graphs, audit gates, and human review queues as first-class artifacts.

[Live demo](https://emmmdty.github.io/deep-research-agent/) · [Competitive landscape](./docs/final/COMPETITIVE_LANDSCAPE.md) · [Repository map](./docs/REPO_MAP.md) · [Related work](#related-work-and-references)

### 60-Second Tour

1. **Ask** — type any research question on the landing page.
2. **Online retrieval** — the demo actually executes a real multi-source retrieval against
   Wikipedia / OpenAlex / Crossref (no key, no agent): queries are organized by fixed rules and
   every excerpt links to its live source. The page states clearly that an agent requires an
   LLM; the full multi-agent system (planning, parallel research, evidence audit, report
   delivery) runs in this repository and needs configured model credentials (see Quick Start).
3. **Reports** — every conclusion shows its source excerpts; browse the built-in demo case
   library as a replay.
4. **Benchmark** — direct answers to "is multi-agent worth it" backed by deterministic
   ablations, plus the sourced industry comparison.
5. **Architecture** — how it is implemented (task DAG, bounded scheduler, governed gateways,
   evidence store, product API).

## Architecture At A Glance

![Deep Research Agent user-facing architecture](./docs/assets/architecture-overview.png)

The canonical runtime is `src/deep_research_agent/`:

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Agent roles | `agents/` (`planner.py`, `researcher.py`, `critic.py`, `factory.py`) | `LLMResearchPlanner` generates sub-objectives (deterministic fallback); `LLMResearcherWorker` plans queries, calls governed search tools, and extracts verbatim-grounded claims; `LLMCriticWorker` resolves contradictions and synthesizes the report; the default `SCHEDULER_FACTORY_PATH` composes them with the tool gateway |
| Agent orchestration | `orchestration/` (`dag.py`, `scheduler.py`, `workers.py`, `reducer.py`) | Compile a research brief into an immutable task DAG; bounded asyncio scheduler runs ready tasks in parallel (up to 8 workers) with typed message passing |
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
user topic → LLMResearchPlanner.plan() [deterministic fallback; required-objective
   coverage check appends any objectives the model missed] → ResearchDAG
   (research tasks ∥ critic task)
   → ResearchScheduler.run() [bounded asyncio, ≤8 workers, typed TaskSpec/WorkerOutput]
   → LLMResearcherWorker — native function-calling agentic loop:
       plan_queries() → governed ToolGateway (web/GitHub/arXiv, budget+idempotency)
       → assess_coverage() reflection → follow-up queries when evidence is thin
       → select_pages() → governed fetch_page() full-document reading → chunking
       → submit_claims() schema-constrained extraction, every claim grounded in a
         verbatim evidence span (longest-verbatim-span matcher, else claim dropped)
     [chat clients without function calling degrade to prompt-based JSON extraction]
   → LLMCriticWorker: contradiction review (grounded CriticDecisions)
     → deterministic EvidenceReducer + EvidenceAuditor audit
   → ReportBundleCompilerV2.compile() → report_bundle.json + report.md/html
   → job artifacts under workspace/research_jobs/<job_id>/
```

Every critical claim in the bundle must resolve to an evidence span inside the frozen corpus
manifest; unverifiable claims are routed to a human review queue. Offline mode
(`SCHEDULER_RUNTIME_MODE=offline`) swaps in the deterministic benchmark pipeline so the whole
runtime is demonstrable without credentials. The full lifecycle is documented in
[docs/architecture.md](./docs/architecture.md) and [docs/USER_GUIDE.md](./docs/USER_GUIDE.md).

## Evaluation & Benchmark Evidence

The release gate is deterministic and reproducible locally — no API keys, no network. A
second, **live agent lane** captures real model-driven runs with real-time search as
committed evidence. The two lanes are never conflated: deterministic metrics prove
pipeline correctness against frozen fixtures; the live lane reports real answers on real
benchmark questions, including where the system fails.

### Live Lane — Real Benchmarks (the honest numbers)

The canonical scheduler-v2 agent (live LLM + governed web/GitHub/arXiv search +
full-page reads + injection guardrails) runs real questions from public benchmark sets;
every per-question bundle, checkpoint, and judge rationale is committed.

| Benchmark | Run | Result |
| --- | --- | --- |
| **GAIA 2023 validation** | [`evals/reports/live_benchmarks/gaia_real/`](./evals/reports/live_benchmarks/gaia_real/) | 20 text-only questions (L1=7, L2=8, L3=5): **7/20 judge-correct (35%), 5/20 exact match (25%)**; L1 57% · L2 25% · L3 20%; ~7.1M tokens, ~$7.1, 36 min. Two of those correct answers came from fixing a critic crash the benchmark surfaced (see error analysis). |
| **BrowseComp** | [`evals/reports/live_benchmarks/browsecomp_real/`](./evals/reports/live_benchmarks/browsecomp_real/) | 15 questions (stratified by topic) from the official 1266: real runs with committed per-question artifacts. |
| **Head-to-head** | [`evals/reports/live_benchmarks/head_to_head/`](./evals/reports/live_benchmarks/head_to_head/) | ours (canonical agent) vs langchain-ai open_deep_research vs gpt-researcher on the same topics, blind LLM judge, same endpoint/model. |
| **Model comparison** | [`evals/reports/live_benchmarks/model_comparison/`](./evals/reports/live_benchmarks/model_comparison/) | 3 topics through the same pipeline; the configured endpoint serves a single model, so this documents the harness plus one full lane (judge Ø 7.67) and the endpoint constraint. |
| **Error analysis** | [`docs/final/ERROR_ANALYSIS.md`](./docs/final/ERROR_ANALYSIS.md) | Failure taxonomy of the live lane: a critic crash eliminated 25% of correct answers (fixed + re-measured), multi-hop facts, wrong-fact selection, and structurally unanswerable image questions. |

### Deterministic Lane — Pipeline Correctness

| Evidence | Where | Result |
| --- | --- | --- |
| Authoritative smoke gate | `evals/reports/phase5_local_smoke/` | 5 suites × smoke_local, all passed |
| Native regression | `evals/reports/native_regression/` | company12/industry12/trusted8/file8/recovery6 passed |
| Headline metrics (deterministic lane) | `evals/reports/followup_metrics/headline_metrics.json` | completion rate: `1.0`, critical claim support precision: `1.0`, citation error rate: `0.0`, policy compliance rate: `1.0` (fixture runs, 0 provider tokens by design — these measure pipeline correctness, not answer quality) |
| Ablations (multi-agent value) | `evals/reports/followup_metrics/ablation_summary.md` | see table below |
| **Live agent run (real LLM + real search)** | [`evals/reports/live_agent/`](./evals/reports/live_agent/README.md) | real scheduler-v2 job: 30 accepted claims over 28 frozen sources, 12 governed search calls, 23 LLM calls, 104K tokens, ~$0.10; bundle + scheduler trace committed |
| **Live route demo (agentic loop)** | [`evals/reports/live_route_demo/`](./evals/reports/live_route_demo/README.md) | Hangzhou→Dongguan routing with three personas (Loong Air 365 flight pass, student ticket, general): 5 parallel researcher agents, 39 governed searches, 20 full-page reads (incl. 12306 official pages), 3 reflection follow-up rounds, 261 accepted claims / 1 qualified over 98 frozen sources; planner coverage check auto-added the missed Loong Air objective; human-verified ground-truth table included |
| External benchmark adapters | `evals/external/` + `portfolio_summary.json` | BrowseComp/GAIA/LongBench-v2/LongFact/Facts grounding guarded smoke (fixture-based integrity lanes; the real runs above are separate and honest) |
| Value scorecard | [docs/final/VALUE_SCORECARD.md](./docs/final/VALUE_SCORECARD.md) | full metric definitions and results, split into deterministic vs live lanes |
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
requires working LLM credentials in `.env`; production composes the built-in model-driven
agent (`deep_research_agent.agents.factory:build_scheduler_factory`) with governed
web/GitHub/arXiv search. Enable the model-driven planner with `AGENT_PLANNER_ENABLED=true`.

```bash
# real agent: LLM planner + governed live search + LLM researcher/critic
SCHEDULER_RUNTIME_MODE=production AGENT_PLANNER_ENABLED=true \
  uv run python main.py submit --topic "What did OpenAI announce for agents in 2026?" --json
```

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
- The deterministic eval lane is authoritative for pipeline correctness; the live lane reports
  real (and honest, sometimes low) scores on real benchmark questions with a committed failure
  analysis. Live-provider quality/cost comparisons across models are limited by the configured
  endpoint, which currently serves a single model (see the model-comparison report).
- Open-web search is discovery-only; critical claims are limited to governed, frozen sources.
- The pipeline is text-only: GAIA-style questions that require reading an image or photograph
  are a documented failure class in the error analysis.
- Memory is explicit CRUD plus subject-scoped recall; conversation-to-memory promotion is roadmap.
- The model-driven agents assume a configured OpenAI-compatible endpoint; failure degrades
  planner/query steps to deterministic fallbacks but claim grounding fails closed (no fake claims).

## Roadmap

- Measure and harden queue/object-storage adapters after the Postgres/MinIO profile is exercised.
- Live-provider head-to-head comparisons (ours vs open_deep_research vs gpt-researcher) with cost
  and quality telemetry.
- Expand GAIA/BrowseComp guarded subset coverage; review integrity findings before scaling.
- Human-in-the-loop review flows that recompile or annotate delivered bundles.
- Tool-calling dispatch (model chooses which tools to call) over the current governed
  query-plan loop.

## Related Work And References

The architecture deliberately borrows patterns from the following open projects and systems:

- [OpenAI Deep Research / Agents SDK](https://github.com/openai/openai-agents-python) — sub-agent
  decomposition, tool governance; we add frozen-corpus provenance and deterministic audit gates.
- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —
  the checkpoint/recovery and citation-attribution pain points this project targets.
- [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) —
  planner/researcher/critic loop shape; we bound the loop with a validated DAG and budget caps.
- [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) — parallel sub-question
  research with web grounding; compared in the [competitive landscape](./docs/final/COMPETITIVE_LANDSCAPE.md).
- [STORM](https://github.com/stanford-oval/storm) — outline-driven multi-perspective writing.
- [Model Context Protocol](https://github.com/modelcontextprotocol/modelcontextprotocol) — tool
  interface conventions mirrored by the governed tool gateway.

## License

MIT. See [LICENSE](./LICENSE).
