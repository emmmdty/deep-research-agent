# GUI Backlog

## Phase 20 Decision Freeze
- Verdict: `READY_FOR_WEB_GUI`.
- Delivery order: web GUI first, desktop wrapper later.
- API strategy: consume the existing local FastAPI surface and CLI/eval artifacts; do not redesign runtime or provider layers.
- Event strategy: poll `GET /v1/research/jobs/{job_id}/events?after_sequence=<n>`.
- Benchmark strategy: browse committed native artifacts first; add bounded local run buttons only after the web shell and benchmark page exist.
- Desktop strategy: defer validated Tauri work because Rust/Cargo are missing locally.

## Phase 21 - Web GUI Scaffold
- Create `apps/gui-web/` with React, TypeScript, Vite, npm scripts, and local dev documentation.
- Establish app routes for Jobs, Artifacts, Benchmarks, Docs/Help, and Settings/About.
- Build an operator/reviewer layout with navigation, dense cards, detail panes, and no chat-bubble primary UI.
- Add a typed API client for the current local FastAPI contract.
- Add shared view models for `PublicJob`, `PublicJobEvent`, `ArtifactName`, `ArtifactLink`, native benchmark summary, and local settings.
- Add local API base URL configuration, defaulting to `http://127.0.0.1:8000`.
- Add a client-side known-job registry because no job-list endpoint exists.
- Acceptance: `npm install`, `npm run dev`, and the app shell render without backend code changes.

## Phase 22 - Research Job UX
- Implement a submit form for `topic`, `max_loops`, `research_profile`, `source_profile`, `allow_domains`, `deny_domains`, `connector_budget`, and `start_worker`.
- Implement a job detail page that loads `GET /v1/research/jobs/{job_id}` and displays lifecycle `status` separately from `audit_gate_status`.
- Implement event polling with `after_sequence`, backoff, and a clear paused/error state.
- Implement bounded action buttons for cancel, retry, resume, refine, and review using the existing API routes.
- Implement a report/artifact viewer using `artifact_urls`, with `report.html` preferred and `report_bundle.json` as the authoritative fallback.
- Implement structured inspectors for claims, sources, audit decision, review queue, claim graph, and trace.
- Acceptance: a user can submit a local no-worker job, inspect status/events, and open available artifacts without direct filesystem paths.

## Phase 23 - Native Benchmark Console
- Implement a native benchmark overview page for `smoke_local` and `regression_local`.
- Show suite cards for `company12`, `industry12`, `trusted8`, `file8`, and `recovery6`.
- Read or embed links to `docs/benchmarks/native/NATIVE_SCORECARD.md`, `CASEBOOK.md`, `USAGE_GUIDE.zh-CN.md`, and committed JSON manifests.
- Add suite detail views for task counts, status, key metrics, report links, and bundle links.
- Add casebook deep links for selected representative cases.
- Defer external benchmark UI.
- If run buttons are added, label them local, deterministic, and bounded; use documented CLI commands and explicit output roots.
- Acceptance: a reviewer can understand native benchmark coverage from the GUI without reading the repo tree manually.

## Phase 24 - Desktop Shell and Handoff Docs
- Re-check `rustc --version`, `cargo --version`, and Tauri prerequisites after the web GUI is stable.
- If prerequisites are available, scaffold a Tauri 2 wrapper around the existing web build without moving business logic into Rust.
- If prerequisites are missing, leave blocker docs and do not block web GUI completion.
- Add GUI usage docs under `docs/gui/`.
- Add screenshots or static assets only if generated during GUI validation.
- Acceptance: either a runnable desktop wrapper exists or a documented scaffold/blocker explains the exact missing prerequisites.

## Future Backend Candidates
- Add `GET /v1/research/jobs` for local job listing.
- Add read-only benchmark summary endpoints if the GUI should avoid reading committed files or shelling out.
- Add a server-side artifact index endpoint if `manifest.json` needs a stable API projection.
- Add optional API health endpoint for GUI startup diagnostics.

## Explicit Non-goals
- No chat-first UI.
- No provider-backed full native execution in the GUI run.
- No external benchmark integration.
- No auth, tenant, remote queue, or object store implementation.
- No runtime, provider, connector, audit, or eval redesign during GUI app phases.
