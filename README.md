# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

An evidence-first Deep Research Agent for company and industry research.

This repository is built around:

- a deterministic async job runtime
- source policy and snapshotting
- claim-level audit and review queue artifacts
- report bundles as the authoritative machine-readable output
- OpenAI / Anthropic provider abstraction
- CLI, local HTTP API, and batch entrypoints

It is not a chat shell, not a frontend, and not a “more agents = better” demo.

## Public Surfaces

### CLI

The supported developer CLI lives behind `main.py`:

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

### Local HTTP API

Phase 4 adds a local FastAPI surface over the same deterministic job runtime:

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

This is a real local API, but it is still backed by the local SQLite/filesystem runtime. It is not an auth-enabled, multi-tenant production service.

## Quickstart

### 1. Install dependencies

```bash
uv sync --group dev
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Fill in the required provider and search credentials before running live research commands.

### 3. Submit a job from the CLI

```bash
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --max-candidates-per-connector 4 \
  --max-fetches-per-task 3 \
  --max-total-fetches 8

uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
uv run python main.py bundle --job-id <job_id> --json
```

### 4. Start the local HTTP API

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

Then submit and inspect a job:

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs \
  -X POST \
  -H 'content-type: application/json' \
  -d '{
    "topic": "AI coding agent market map",
    "max_loops": 2,
    "research_profile": "default",
    "source_profile": "industry_broad",
    "start_worker": false
  }'

curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/events
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
```

### 5. Run a batch file

Create `batch.jsonl`:

```jsonl
{"topic":"Anthropic company profile","max_loops":1,"research_profile":"default","start_worker":false}
{"topic":"AI coding agent market map","max_loops":2,"research_profile":"benchmark","source_profile":"industry_broad","start_worker":false}
```

Submit it:

```bash
uv run python main.py batch run --file batch.jsonl --json
```

### 6. Run local evals and the release smoke pack

```bash
uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json
uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
```

The committed Phase 5 local smoke outputs live under `evals/reports/phase5_local_smoke/`.

## Artifact Contract

Completed jobs write their runtime artifacts under `workspace/research_jobs/<job_id>/`.

The stable artifact names are:

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

`report_bundle.json` is the authoritative machine-readable output. The sidecar files are derived delivery and audit views.

## Source Profiles

Canonical source profiles are:

- `company_trusted`
- `company_broad`
- `industry_trusted`
- `industry_broad`
- `public_then_private`
- `trusted_only`

## Repository Layout

The canonical execution path now lives under `src/deep_research_agent/`:

```text
src/deep_research_agent/
  gateway/          CLI, HTTP API, batch helpers, public contracts
  research_jobs/    deterministic runtime, store, service, worker, orchestrator
  connectors/       search / fetch / file-ingest substrate and snapshot store
  auditor/          claim audit, review queue, audit sidecars
  reporting/        bundle compiler and delivery artifacts
  providers/        provider routing and abstraction
  evidence_store/   evidence storage primitives
  evals/            deterministic local suite runner and eval contracts
evals/              suite definitions, frozen datasets, rubrics, committed smoke outputs
legacy/             archived workflow path retained for compatibility only
tests/              runtime, connector, auditor, and public-surface regressions
docs/               architecture, development, ADRs, and migration notes
```

## Development

Key local checks:

```bash
uv run python main.py --help
uv run ruff check .
uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke
```

For broader validation, see:

- [Architecture](./docs/architecture.md)
- [Development Guide](./docs/development.md)
- [Final Change Report](./FINAL_CHANGE_REPORT.md)
- [Experiment Summary](./docs/final/EXPERIMENT_SUMMARY.md)
- [API Contract](./specs/api-readiness-contract.md)
- [ADR-0008](./docs/adr/adr-0008-http-api-surface.md)
- [ADR-0009](./docs/adr/adr-0009-batch-and-artifact-contract.md)
- [Phase 4 Migration Note](./docs/migrations/phase4-surface-migration.md)

## Current Limits

- The local HTTP API still uses SQLite, filesystem artifacts, and local subprocess workers.
- There is no auth, tenant isolation, external queue, or object storage layer yet.
- Review writes are append-only and visible through runtime events and sidecars, but they do not fully recompile the report bundle JSON in Phase 4.
- `legacy-run` is still present as a hidden compatibility path and is not the supported public runtime.
- The heavy benchmark/comparator stack still exists for diagnostics, but the Phase 5 release gate now depends on local claim-centric suite manifests under `evals/`.

## License

MIT. See [LICENSE](./LICENSE).
