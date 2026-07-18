# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

An evidence-first multi-agent research product for scholarly and industry analysis, built around auditable report bundles instead of chat-only answers.

## Core Architecture

- `src/deep_research_agent/gateway/`: CLI, local HTTP API, batch commands, and artifact access.
- `src/deep_research_agent/research_jobs/`: deterministic job lifecycle with checkpoints, events, cancellation, retry, resume, and refinement.
- `src/deep_research_agent/connectors/`: web, GitHub, arXiv, and file ingestion through source policy and snapshotting.
- `src/deep_research_agent/auditor/`: claim graph, support edges, conflict sets, audit decisions, and review queues.
- `src/deep_research_agent/reporting/`: report bundle compiler and sidecar artifact emission.
- `src/deep_research_agent/providers/`: OpenAI, Anthropic, and compatible-provider routing.
- `src/deep_research_agent/product/`: PostgreSQL-backed topics, conversations, runs, memories, and tenant boundaries.
- `src/deep_research_agent/corpus/`: governed scholarly ingestion, immutable manifests, parser fallback, and public content cache.
- `src/deep_research_agent/observability/`: credential-safe OpenTelemetry spans and Phoenix export.

The canonical runtime is `src/deep_research_agent/`. Root packages with names such as `services/`, `connectors/`, `artifacts/`, `policies/`, `tools/`, and `evaluation/` are compatibility or diagnostic layers. See [Repository Map](./docs/REPO_MAP.md).

## Repository Layout

```text
src/deep_research_agent/  canonical runtime
apps/gui-web/             optional local reviewer UI
docker-compose.yml        V2 API, Web, worker, PostgreSQL/pgvector, MinIO, GROBID, Phoenix
apps/desktop-tauri/       experimental desktop wrapper
configs/                  runtime and source-profile config
schemas/                  JSON artifact and runtime contracts
evals/                    deterministic eval assets and reports
docs/                     reviewer docs and archives
tests/                    regression tests
scripts/                  smoke, eval, and diagnostic commands
legacy/                   archived graph-first paths
```

## Quick Run

```bash
uv sync --group dev
cp .env.example .env
uv run python main.py --help
```

## V2 Web Demo

The supported product path is the authenticated V2 workspace. Copy `.env.example`, replace every
placeholder secret, choose `SCHEDULER_RUNTIME_MODE=offline` for a credential-free deterministic
demo, and run:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`. The Web container is the same-origin entrypoint and proxies API and
SSE traffic to the internal service. Production mode requires a real
`SCHEDULER_FACTORY_PATH`; it never silently falls back to offline execution.

Submit a local job without starting a worker:

```bash
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --no-worker \
  --json
```

Start the local API:

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

Run the core smoke checks:

```bash
uv run python main.py --help
uv run ruff check .
uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
```

## Artifact Contract

Completed jobs write artifacts under `workspace/research_jobs/<job_id>/`.

Stable artifact names:

- `report_bundle.json` as the authoritative machine-readable output
- `report.md` and `report.html` as reader-facing renderings
- `claims.json`, `sources.json`, `audit_decision.json`, `review_queue.json`, and `claim_graph.json` as audit sidecars
- `trace.jsonl`, `manifest.json`, and `review_actions.jsonl` as execution and review records

Access artifacts through the CLI:

```bash
uv run python main.py bundle --job-id <job_id> --json
```

or through the local API:

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/artifacts/report_bundle.json
```

## Evaluation Summary

The merge-safe gate is the local deterministic smoke pack under `evals/reports/phase5_local_smoke/`. The reviewer-facing deterministic regression evidence lives under `evals/reports/native_regression/` and [docs/benchmarks/native](./docs/benchmarks/native/README.md).

Key committed metrics from the value scorecard include:

- completion rate: `1.0`
- bundle emission rate: `1.0`
- critical claim support precision: `1.0`
- citation error rate: `0.0`
- policy compliance rate: `1.0`
- resume success rate: `1.0`

For details, read [Experiment Summary](./docs/final/EXPERIMENT_SUMMARY.md) and [Value Scorecard](./docs/final/VALUE_SCORECARD.md).

## Local UI

The optional reviewer/operator UI lives in `apps/gui-web/` and consumes the local API.

```bash
cd apps/gui-web
npm install
npm run dev
```

For local Vite development, set `VITE_DRA_API_BASE_URL` to the API origin and configure the API
server's explicit development origin if the UI and API are on different ports. Compose uses the
same-origin proxy so browser credentials and SSE reconnects work without wildcard CORS.

Optional desktop packaging experiments live under `apps/desktop-tauri/`. See [GUI docs](./docs/gui/README.md).

## Supported Questions And Source Limits

The first domain pack covers how event graphs, agents, and LLMs interact. Users can request
source-grounded literature maps, method comparisons, exact claim-to-span evidence, contradiction
reviews, and explicit refreshes. The API asks for clarification before expensive or underspecified
jobs and keeps follow-ups on the frozen report snapshot until a refresh is requested.

Critical claims are limited to governed, frozen sources: arXiv, ACL Anthology, OpenAlex, Crossref,
DataCite, DBLP, PMLR, NeurIPS proceedings, and licensed uploads. Open-web search is discovery-only
and cannot support a critical claim. A source outage creates a freshness warning.

## Current Limits

- The Docker profile is a small-team deployment, not a horizontally scaled SaaS control plane.
- Runtime execution still uses job-local subprocesses and a recovery worker; there is no Redis queue.
- Live web research depends on configured provider/search credentials and external network availability.
- Legacy comparator and report-shape diagnostics remain available, but claim-centric bundle/eval outputs are the release story.
- The project is not a multi-tenant SaaS and not a "more agents = better" demo.

## Roadmap

- Measure and harden external queue/object-storage adapters only after the current Postgres/MinIO profile is exercised.
- Expand claim-support evaluation beyond deterministic smoke/regression suites.
- Harden provider routing with capability, health, cost, and rate-limit signals.
- Improve review flows so human decisions can recompile or annotate delivered bundles.
- Keep legacy diagnostic code out of the public product path.

## License

MIT. See [LICENSE](./LICENSE).
