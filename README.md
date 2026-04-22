# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

An evidence-first Deep Research Agent for company and industry research.

## Measured Value

A deterministic, evidence-first Deep Research Agent that emits grounded report bundles instead of chat-only answers.

Committed follow-up metrics from `evals/reports/followup_metrics/`:

- `completion_rate=1.0`
- `bundle_emission_rate=1.0`
- `critical_claim_support_precision=1.0`
- `citation_error_rate=0.0`
- `policy_compliance_rate=1.0`
- `resume_success_rate=1.0`
- `stale_recovery_success_rate=1.0`
- `ttfr_seconds_p50=1.344091`

Review paths:

- [Value Scorecard](./docs/final/VALUE_SCORECARD.md)
- [Experiment Summary](./docs/final/EXPERIMENT_SUMMARY.md)
- [Native Scorecard](./docs/benchmarks/native/NATIVE_SCORECARD.md)
- [Native Casebook](./docs/benchmarks/native/CASEBOOK.md)
- [Native Usage Guide (zh-CN)](./docs/benchmarks/native/USAGE_GUIDE.zh-CN.md)
- [Native Optimization Report](./docs/final/NATIVE_OPTIMIZATION_REPORT.md)
- [Release Manifest](./evals/reports/phase5_local_smoke/release_manifest.json)

The HTTP API is still local-only. This repository is not a multi-tenant production SaaS.

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
- `benchmark run`

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

### 6. Run local evals, the release smoke pack, and the native regression layer

```bash
uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json
uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json
uv run python main.py eval run --suite company12 --variant regression_local --output-root evals/reports/native_regression/company12 --json
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json
uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json
```

The committed Phase 5 local smoke outputs under `evals/reports/phase5_local_smoke/` remain the authoritative merge-safe gate.
The committed deterministic native regression outputs live under `evals/reports/native_regression/`, with reviewer-facing docs under `docs/benchmarks/native/`.
The latest benchmark-hardening comparison lives under `evals/reports/native_optimization/`.

### 7. Run an external benchmark smoke and refresh the portfolio summary

```bash
uv run python main.py benchmark run --benchmark facts_grounding --split open --subset smoke --output-root evals/external/reports/facts_grounding_open_smoke --json
uv run python scripts/build_benchmark_portfolio_summary.py --output-root evals/external/reports/portfolio_summary --json
```

The benchmark portfolio is layered:

- authoritative release gate: native Phase 5 local smoke suites under `evals/reports/phase5_local_smoke/`
- native regression: reviewer-facing deterministic regression suites under `evals/reports/native_regression/`
- secondary regression: FACTS Grounding open smoke
- external regression: LongFact / SAFE smoke and LongBench v2 short smoke
- challenge track: BrowseComp guarded smoke, GAIA supported subset, and LongBench v2 medium/long challenge policy

Reviewer-facing benchmark docs live under [docs/benchmarks](./docs/benchmarks/README.md), including the repo-native [Native Scorecard](./docs/benchmarks/native/NATIVE_SCORECARD.md).

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
uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression
uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native
uv run python scripts/build_benchmark_portfolio_summary.py --output-root evals/external/reports/portfolio_summary
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
- The external benchmark portfolio is smoke/subset-first and reviewer-facing; it is not a production benchmark service and it does not override the native release gate.

## License

MIT. See [LICENSE](./LICENSE).
