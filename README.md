# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://emmmdty.github.io/deep-research-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

**An evidence-first multi-agent deep research system.** A model-driven planner
decomposes a question into a task DAG; parallel researcher agents run governed
real-time web/GitHub/arXiv search and extract only claims they can ground in
verbatim evidence; a critic audits every claim and synthesizes a report where
every conclusion carries an inline numbered citation into a frozen, immutable
corpus — and what cannot be proven is routed to a human review queue.

This repository is the implementation of one claim, measured honestly: *when
the answer is wrong, you can prove it.*

## Measured Evidence (live lane: real LLM + real search)

Every number below comes from committed live runs of the canonical
scheduler-v2 agent (`src/deep_research_agent/`), not fixture simulations.

| Experiment | Result | Where |
| --- | --- | --- |
| **GAIA 2023 (text-only sample of 20)** | 7/20 judge-correct (35%), 5/20 exact (25%); L1 57% · L2 25% · L3 20%; ~7.1M tokens / ~$7.1 / 36 min | [`gaia_real/`](./evals/reports/live_benchmarks/gaia_real/) |
| **Same-model baseline (control)** | The same model, one call per question, **no tools, no retrieval: 0/20 (0%)** — the entire score comes from the agent machinery, not the model | [`gaia_baseline/`](./evals/reports/live_benchmarks/gaia_baseline/) |
| **Cost analysis** | ~$1.0 per correct answer; incorrect questions burn **1.56x more tokens** — spending more does not buy correctness; the levers are decision quality and the audit gate | [`cost_analysis/`](./evals/reports/live_benchmarks/cost_analysis/) |
| **Citation rendering** | All committed live bundles re-rendered through the deterministic citation injector: every supported claim (**679/679**) is traceable via inline `[n]` references + a numbered `## References` section + a complete `## Claim Register` (previously the reader-facing report showed no citations at all) | [`citation_rendering/`](./evals/reports/citation_rendering/) |
| **BrowseComp** | 15 stratified official questions, real runs, committed per-question artifacts | [`browsecomp_real/`](./evals/reports/live_benchmarks/browsecomp_real/) |
| **Head-to-head** | ours vs langchain-ai `open_deep_research` vs `gpt-researcher`, blind LLM judge, same endpoint. Round 1: lost — the judge explicitly flagged our **missing citations** (a rendering gap, not the evidence system). Round 2 after the fix: `citation_accuracy` 0.0→**1.0**, `source_coverage` 0→**47–95** (competitors: still 0), judge's citation complaints gone; remaining gap is synthesis prose style, honestly documented | [`head_to_head/`](./evals/reports/live_benchmarks/head_to_head/) · [`head_to_head_round2/`](./evals/reports/live_benchmarks/head_to_head_round2/) |
| **Error analysis** | Failure taxonomy of the live lane: a critic crash eliminated 25% of correct answers (fixed + re-measured, 25%→35% and cheaper), multi-hop gaps, wrong-fact selection, image questions (text-only pipeline) | [`docs/ERROR_ANALYSIS.md`](./docs/ERROR_ANALYSIS.md) |
| **Fault-injection fallback benchmark** | 15 deterministic scenarios, one injected fault per decision point (planner / planning / reflection / page read / extraction / critic review+synthesis / tool failures / budget). Control run triggers **0 fallbacks** (healthy path never touches a fallback); every transient fault is absorbed by its designed layer; all 3 persistent-outage scenarios **fail closed with 0 ungrounded claims published**; scheduler-v2 crash-resume recovers from the durable journal with **0 completed tasks redone** | [`fault_injection/`](./evals/reports/fault_injection/) |
| **Agent dimension metrics** | Deterministic per-dimension measurements of one scripted job: grounding acceptance 80% (4/5 verbatim-grounded), 2-round reflection with 1 gap-triggered follow-up, per-stage prompt/token accounting (~1.9K est. tokens/job), tool-cache steady-state hit rate 100%, memory recall@1 100% + noise precision 100% + tenant isolation enforced | [`agent_metrics/`](./evals/reports/agent_metrics/) |

The deterministic lane (fixture-based, 0 provider tokens) proves *pipeline
correctness*, not answer quality — completion rate: `1.0`, critical claim
support precision `1.0`, policy compliance rate: `1.0` on frozen fixtures,
gated by the release smoke (`evals/reports/phase5_local_smoke/`). It is
deliberately reported separately and never conflated with the live numbers.
Full metric definitions: [`docs/VALUE_SCORECARD.md`](./docs/VALUE_SCORECARD.md),
[`docs/EXPERIMENT_SUMMARY.md`](./docs/EXPERIMENT_SUMMARY.md).

## What The Benchmarks Changed

The live lane is not decoration; it has driven three real fixes:

1. **Critic crash** — 5/20 questions produced no report because critic
   decisions failed schema validation. Fixed with a deterministic report
   fallback; same 20 questions re-run: +2 correct, less cost.
2. **Citation rendering gap** — the head-to-head judge penalized our reports
   for "missing citations" even though every claim is evidence-grounded. Added
   `reporting/citations.py`: a deterministic injector that attaches inline
   `[n]` references, a numbered `## References` section, and a complete
   `## Claim Register`, plus a per-bundle citation coverage audit in
   `audit_summary.report_citation_coverage`.
3. **No control experiment** — added the same-model no-agent GAIA baseline to
   separate model ability from agent value (result above: 0/20 vs 7/20).
4. **Reflection fallback was an anti-pattern** — a failed coverage assessment
   used to be treated as "covered" (optimistic skip). It now falls back
   conservatively to `covered=False` and continues searching, bounded by the
   round budget. The healthy path is unchanged (fault-injection control run:
   0 fallback triggers).
5. **scheduler-v2 crash recovery was cosmetic** — checkpoints were persisted
   only after a run finished, so a killed worker restarted the whole DAG. Task
   checkpoints are now journaled to disk the moment each task completes, and a
   fresh worker resumes from the journal (`run.resumed` event, completed work
   never redone).

## Architecture

![Architecture overview](./docs/assets/architecture-overview.png)

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Agent roles | `agents/` | `LLMResearchPlanner` (objectives + coverage check), `LLMResearcherWorker` (native function-calling loop: plan queries → governed tools → coverage reflection → full-page reads → grounded claims), `LLMCriticWorker` (contradiction review + synthesis) |
| Orchestration | `orchestration/` | Immutable task DAG, bounded asyncio scheduler (≤8 workers), typed message passing, branch-local retry, cancellation |
| Governance | `tool_gateway/`, `policy/` | Role allow-lists, budgets, idempotency, caching, prompt-injection guardrails |
| Evidence & audit | `auditor/`, `evidence_store/` | Claim graph with support edges, frozen corpus manifests, human review queues |
| Deliverable | `reporting/` | Deterministic reduction → audit → citation injection → `report_bundle.json` + `report.md/html` |
| Reliability | `research_jobs/`, `observability/` | Checkpoints, leases, resume/retry, cost tracking, OpenTelemetry spans |
| Product | `gateway/`, `product/`, `apps/gui-web/` | CLI, local HTTP API (SSE), multi-tenant product API, React workspace |

Run shape: `topic → planner → ResearchDAG → scheduler → parallel researchers
→ critic → audit → bundle`. Every critical claim in the bundle resolves to an
evidence span in the frozen corpus manifest; unverifiable claims go to a
review queue. Offline mode (`SCHEDULER_RUNTIME_MODE=offline`) swaps in the
deterministic pipeline so the runtime is fully demonstrable without
credentials. See [`docs/architecture.md`](./docs/architecture.md).

## Demo

- **Live demo** — https://emmmdty.github.io/deep-research-agent/ . The
  featured case is a **real online agent run replay** (Hangzhou → Dongguan
  with three personas): 5 parallel researchers, 39 governed searches, 20
  full-page reads including official 12306 pages, 3 reflection rounds, 261
  grounded claims, human-verified ground truth.
- **Locally** — `npm run dev --prefix apps/demo-site` (static, no keys), or
  the full product stack with `docker compose up --build`.

## Quick Start

```bash
uv sync --group dev
cp .env.example .env        # offline demo needs no secrets
uv run python main.py --help
```

Deterministic offline mode (no API keys, no network): `submit` falls back to
the deterministic orchestrator-v1 benchmark pipeline so the demo produces a
report without credentials.

```bash
SCHEDULER_RUNTIME_MODE=offline uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted --allow-domain anthropic.com --json
```

Real agent (LLM planner + governed live search + researcher/critic) with
credentials in `.env` — `submit` defaults to the canonical scheduler-v2 runtime;
use `--legacy` to force the older orchestrator-v1 pipeline:

```bash
SCHEDULER_RUNTIME_MODE=production uv run python main.py submit \
  --topic "What did OpenAI announce for agents in 2026?" --json
```

The runtime never silently falls back from production to offline execution.

## Current Limits

- Deployment is a small-team Compose stack, not a horizontally scaled SaaS.
- Text-only pipeline; GAIA image questions are a documented failure class.
- Live comparisons are limited by the configured endpoint (single model).
- Memory is explicit CRUD + subject-scoped recall; conversation-to-memory
  promotion is roadmap.
- Open-web search is discovery-only; critical claims are limited to governed,
  frozen sources (fails closed, never fakes evidence).

## Roadmap

- Live budget sweep (max_tool_calls / rounds vs accuracy) on fixed questions.
- Tool-calling dispatch (model chooses tools) over the governed query loop.
- Human-in-the-loop review that recompiles delivered bundles.
- Live provider head-to-heads with cost/quality telemetry.

## Repository Layout

```text
src/deep_research_agent/  canonical runtime (agents, orchestration, auditor, reporting, product)
apps/gui-web/             React product workspace
apps/demo-site/           static GitHub Pages demo (real-run replay + benchmark evidence)
evals/                    live-lane evidence, deterministic eval assets, fixtures
docs/                     reviewer docs (architecture, evaluation, error analysis)
scripts/                  live runners, eval, demo-data, and analysis commands
legacy/                   archived graph-first runtime (non-product, read-only)
```

## Related Work And References

- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — checkpoint/recovery and citation-attribution pain points this project targets.
- [OpenAI Deep Research / Agents SDK](https://github.com/openai/openai-agents-python) — sub-agent decomposition, tool governance.
- [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) — planner/researcher/critic shape; compared in the head-to-head.
- [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) — parallel sub-question research; compared in the head-to-head.
- [STORM](https://github.com/stanford-oval/storm) — outline-driven multi-perspective writing.
- [Model Context Protocol](https://github.com/modelcontextprotocol/modelcontextprotocol) — tool interface conventions mirrored by the governed tool gateway.

## License

MIT. See [LICENSE](./LICENSE).
