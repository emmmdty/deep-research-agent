# GUI Job Flow

This runbook covers the Phase 22 local web GUI path for submitting and inspecting Deep Research Agent jobs. The flow stays bounded: submissions use `start_worker=false`, so the GUI can validate the API contract without launching a long-running worker.

## Start Services

From the repository root:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn deep_research_agent.gateway.api:app --host 127.0.0.1 --port 8000
```

From the web app directory:

```bash
cd apps/gui-web
npm install
npm run dev
```

Open the Vite URL printed by `npm run dev`.

## Submit A Bounded Job

1. In `New local research job`, enter a topic such as `Anthropic company profile`.
2. Choose a source profile, for example `company_trusted`.
3. Select `Submit local job`.
4. Confirm the returned job id appears in `Known Jobs` and `Job detail`.

Expected API call:

```http
POST /v1/research/jobs
```

The request body includes `start_worker: false`, `max_loops: 1`, the topic, and the selected source profile.

## Inspect Existing Job Evidence

1. Paste a job id into `Manual job id`.
2. Select `Load job`.
3. Confirm `Status`, `Audit gate`, `Stage`, and `Blocked critical claims` are visible.
4. Confirm lifecycle events are loaded from `/v1/research/jobs/{job_id}/events?after_sequence=0`.
5. Select `Load bundle` to inspect the JSON report bundle.

The bundle inspector intentionally renders raw JSON first. Later GUI phases can add specialized claims, sources, audits, and trace panes without changing the backend contract.

## Local Verification

Phase 22 was verified with:

```bash
cd apps/gui-web
npm test
npm run lint
npm run build
```

Backend boundary checks:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts
```
