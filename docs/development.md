# Development Guide

This guide describes the current Phase 4 developer workflow.

## Environment

```bash
git clone https://github.com/emmmdty/deep-research-agent.git
cd deep-research-agent
uv sync --group dev
cp .env.example .env
```

Fill in the provider and search credentials you need for live runs.

## Supported Local Commands

### CLI lifecycle

```bash
uv run python main.py submit --topic "Anthropic company profile"
uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
uv run python main.py cancel --job-id <job_id>
uv run python main.py retry --job-id <job_id>
uv run python main.py resume --job-id <job_id>
uv run python main.py refine --job-id <job_id> --instruction "Expand competitor coverage."
uv run python main.py bundle --job-id <job_id> --json
```

Notes:

- `submit`, `retry`, `resume`, and `refine` accept `--no-worker`
- `bundle` defaults to `report_bundle.json`
- `bundle --artifact-name manifest.json` reads a specific sidecar

### CLI batch

```bash
uv run python main.py batch run --file batch.jsonl --json
```

`batch run` accepts:

- JSON array files
- JSONL files with one submit payload per line

Each item uses the same request shape as `POST /v1/research/jobs`.

### Local HTTP API

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

Representative requests:

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
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/artifacts/manifest.json
```

## Artifact Layout

Completed jobs write into:

```text
workspace/research_jobs/<job_id>/
  report.md
  bundle/
    report.html
    report_bundle.json
    claims.json
    sources.json
    audit_decision.json
    manifest.json
    trace.jsonl
  audit/
    claim_graph.json
    review_queue.json
    review_actions.jsonl
```

## Validation Commands

### Focused public-surface regression

```bash
uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
```

### Runtime + connector + auditor regression slice

```bash
uv run pytest -q \
  tests/test_phase2_jobs.py \
  tests/test_phase3_connectors.py \
  tests/test_phase4_auditor.py \
  tests/test_phase4_surfaces.py \
  tests/test_cli_runtime.py
```

### Lint

```bash
uv run ruff check .
```

### Help smoke

```bash
uv run python main.py --help
```

## Practical Smoke Flow

### CLI smoke without worker

```bash
WORKSPACE_DIR=workspace/phase4-cli-smoke \
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --no-worker \
  --json
```

Then inspect the created runtime row with:

```bash
WORKSPACE_DIR=workspace/phase4-cli-smoke \
uv run python main.py status --job-id <job_id> --json
```

### API smoke without worker

Start the API:

```bash
WORKSPACE_DIR=workspace/phase4-api-smoke \
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

Then submit a local job:

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs \
  -X POST \
  -H 'content-type: application/json' \
  -d '{
    "topic": "Anthropic company profile",
    "max_loops": 1,
    "research_profile": "default",
    "start_worker": false
  }'
```

## Compatibility Notes

- `legacy-run` remains available as a hidden compatibility path only.
- The public API is local and deterministic, not server-grade.
- Benchmark and release scripts remain valid, but they are not the public job API boundary.

## Further Reading

- [README](../README.md)
- [Architecture](./architecture.md)
- [API Contract](../specs/api-readiness-contract.md)
- [ADR-0008](./adr/adr-0008-http-api-surface.md)
- [ADR-0009](./adr/adr-0009-batch-and-artifact-contract.md)
- [Phase 4 Migration](./migrations/phase4-surface-migration.md)
