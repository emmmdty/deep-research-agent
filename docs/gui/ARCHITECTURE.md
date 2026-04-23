# GUI Architecture

## Purpose

The GUI is a local operator/reviewer console for the existing Deep Research Agent. It consumes the repository's current local API, artifact, bundle, and benchmark surfaces without rewriting runtime, provider, eval, or audit code.

## Components

| Area | Path | Responsibility |
| --- | --- | --- |
| Web app | `apps/gui-web/` | React, TypeScript, Vite shell for local operations. |
| API client | `apps/gui-web/src/api/client.ts` | Typed fetch wrapper for the existing FastAPI boundary. |
| Job workspace | `apps/gui-web/src/App.tsx` | Submit bounded jobs, load manual job ids, poll events, inspect bundles. |
| Benchmark view model | `apps/gui-web/src/benchmarkData.ts` | Static GUI snapshot of committed native benchmark evidence. |
| GUI docs | `docs/gui/` | Reviewer/operator handoff docs and demo flows. |
| Desktop scaffold | `desktop/tauri/` | Blocked Tauri handoff location until Rust/Cargo are installed. |

## API Boundary

The GUI uses the existing local FastAPI surface:

- `POST /v1/research/jobs`
- `GET /v1/research/jobs/{job_id}`
- `GET /v1/research/jobs/{job_id}/events`
- `GET /v1/research/jobs/{job_id}/bundle`
- artifact links exposed from job responses

Job submission in the GUI uses `start_worker=false` for bounded local validation. Long-running worker orchestration stays in the backend/CLI layer.

## State Model

- Known jobs are stored in browser `localStorage` under `dra.gui.knownJobs`.
- There is no backend list-jobs endpoint, so the GUI supports manual job-id loading.
- Event loading is polling-compatible via `after_sequence=0`; there is no SSE/WebSocket dependency.
- Bundle inspection renders raw JSON first to preserve the artifact contract.

## Benchmark Model

The benchmark console surfaces committed local evidence:

- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`

The GUI does not add external benchmark integrations and does not launch long-running benchmark jobs from the browser.

## Desktop Boundary

Tauri is intentionally optional. The web GUI is the primary delivery. The desktop wrapper should wrap the same web build and keep backend interaction through the local API. Current status is documented in `docs/gui/DESKTOP_STATUS.md`.
