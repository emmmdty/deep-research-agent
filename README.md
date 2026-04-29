# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

An evidence-first research runtime for company and industry analysis, built around auditable jobs instead of chat-only answers.

## Core Architecture

- `src/deep_research_agent/gateway/`: CLI, local HTTP API, batch commands, and artifact access.
- `src/deep_research_agent/research_jobs/`: deterministic job lifecycle with checkpoints, events, cancellation, retry, resume, and refinement.
- `src/deep_research_agent/connectors/`: web, GitHub, arXiv, and file ingestion through source policy and snapshotting.
- `src/deep_research_agent/auditor/`: claim graph, support edges, conflict sets, audit decisions, and review queues.
- `src/deep_research_agent/reporting/`: report bundle compiler and sidecar artifact emission.
- `src/deep_research_agent/providers/`: OpenAI, Anthropic, and compatible-provider routing.

The canonical runtime is `src/deep_research_agent/`. Root packages with names such as `services/`, `connectors/`, `artifacts/`, `policies/`, `tools/`, and `evaluation/` are compatibility or diagnostic layers. See [Repository Map](./docs/REPO_MAP.md).

## Repository Layout

```text
src/deep_research_agent/  canonical runtime
apps/gui-web/             optional local reviewer UI
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

Optional desktop packaging experiments live under `apps/desktop-tauri/`. See [GUI docs](./docs/gui/README.md).

## Current Limits

- The HTTP API is local-only: no auth, tenant isolation, external queue, or object storage layer.
- Runtime storage is SQLite plus filesystem artifacts.
- Live web research depends on configured provider/search credentials and external network availability.
- Legacy comparator and report-shape diagnostics remain available, but claim-centric bundle/eval outputs are the release story.
- The project is not a multi-tenant SaaS and not a "more agents = better" demo.

## Roadmap

- Promote server profile support: PostgreSQL, Redis Streams, and S3-compatible object storage.
- Expand claim-support evaluation beyond deterministic smoke/regression suites.
- Harden provider routing with capability, health, cost, and rate-limit signals.
- Improve review flows so human decisions can recompile or annotate delivered bundles.
- Keep legacy diagnostic code out of the public product path.

## License

MIT. See [LICENSE](./LICENSE).
