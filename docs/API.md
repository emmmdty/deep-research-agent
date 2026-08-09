# API

Start the local API:

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

## Routes

```text
GET  /v1/health
POST /v1/research/jobs
GET  /v1/research/jobs/{job_id}
GET  /v1/research/jobs/{job_id}/events
POST /v1/research/jobs/{job_id}:cancel
POST /v1/research/jobs/{job_id}:retry
POST /v1/research/jobs/{job_id}:resume
POST /v1/research/jobs/{job_id}:refine
POST /v1/research/jobs/{job_id}:review
GET  /v1/research/jobs/{job_id}/bundle
GET  /v1/research/jobs/{job_id}/artifacts/{artifact_name}
POST /v1/batch/research
```

The authenticated product workspace adds tenant-scoped routers under `/v1/auth`, `/v1/topics`,
`/v1/conversations`, `/v1/runs`, `/v1/corpus`, `/v1/memory`, and `/v1/admin`. They are enabled
when a product database URL is configured; browse them in the OpenAPI docs.

## Health Example

```bash
curl -s http://127.0.0.1:8000/v1/health
```

Response:

```json
{
  "status": "ok",
  "service": "deep-research-agent",
  "version": "0.1.0"
}
```

The local Web UI uses this endpoint to show API connection status.

## Submit Example

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs \
  -H 'content-type: application/json' \
  -d '{
    "topic": "OpenAI company profile",
    "max_loops": 3,
    "research_profile": "default",
    "source_profile": "company_trusted",
    "allow_domains": [],
    "deny_domains": [],
    "connector_budget": null,
    "start_worker": true
  }'
```

## Artifact Example

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/artifacts/report.md
```
