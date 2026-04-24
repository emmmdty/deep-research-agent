# GUI Contract

## Summary
This document freezes the Phase 20 GUI-facing contract for the local Deep Research Agent.

The GUI must consume the current local FastAPI, CLI, and committed artifact surfaces. It must not depend on hidden filesystem paths, external benchmark integration, provider secrets, auth, tenants, or remote queues.

## Product Boundary
- The GUI is an operator/reviewer interface for local research jobs, bundles, claims, audits, and native benchmark evidence.
- The GUI is not a chat shell.
- The GUI is not a production SaaS console.
- The GUI is not a runtime rewrite.
- The local API remains backed by SQLite, filesystem artifacts, and local subprocess workers.

## API Base
- Development default: `http://127.0.0.1:8000`.
- API app: `deep_research_agent.gateway.api:app`.
- OpenAPI title: `Deep Research Agent API`.
- OpenAPI version: `0.1.0`.

## Endpoint Matrix
| Method | Path | Request model | Response model | GUI use |
| --- | --- | --- | --- | --- |
| `POST` | `/v1/research/jobs` | `SubmitJobRequest` | `PublicJobResponse` | Submit one local research job. |
| `GET` | `/v1/research/jobs/{job_id}` | none | `PublicJobResponse` | Load current job status and artifact URLs. |
| `GET` | `/v1/research/jobs/{job_id}/events` | `after_sequence` query | `JobEventsResponse` | Poll ordered job events. |
| `POST` | `/v1/research/jobs/{job_id}:cancel` | `{}` | `PublicJobResponse` | Request cancellation. |
| `POST` | `/v1/research/jobs/{job_id}:retry` | `RetryJobRequest` | `PublicJobResponse` | Create retry attempt. |
| `POST` | `/v1/research/jobs/{job_id}:resume` | `ResumeJobRequest` | `PublicJobResponse` | Resume existing job. |
| `POST` | `/v1/research/jobs/{job_id}:refine` | `RefineJobRequest` | `PublicJobResponse` | Append refinement instruction. |
| `POST` | `/v1/research/jobs/{job_id}:review` | `ReviewJobRequest` | `PublicJobResponse` | Append human review decision. |
| `GET` | `/v1/research/jobs/{job_id}/bundle` | none | JSON bundle | Load authoritative report bundle. |
| `GET` | `/v1/research/jobs/{job_id}/artifacts/{artifact_name}` | none | JSON, HTML, plain text, or NDJSON | Load a stable sidecar artifact by name. |
| `POST` | `/v1/batch/research` | `BatchResearchRequest` | `BatchResearchResponse` | Submit bounded local batches. |

## Request Defaults
`SubmitJobRequest` supports:

- `topic`: required non-empty string.
- `max_loops`: integer, default `3`, minimum `1`.
- `research_profile`: string, default `default`.
- `source_profile`: string, default `company_broad`.
- `allow_domains`: string list.
- `deny_domains`: string list.
- `connector_budget`: optional string-to-integer map.
- `start_worker`: boolean, default `true`.

The GUI should expose canonical source profiles:

- `company_trusted`
- `company_broad`
- `industry_trusted`
- `industry_broad`
- `public_then_private`
- `trusted_only`

## Job View Model
The GUI should model jobs from `PublicJobResponse` with these fields:

- `job_id`
- `topic`
- `status`
- `current_stage`
- `created_at`
- `updated_at`
- `attempt_index`
- `retry_of`
- `cancel_requested`
- `source_profile`
- `budget`
- `policy_overrides`
- `connector_health`
- `audit_gate_status`
- `critical_claim_count`
- `blocked_critical_claim_count`
- `error`
- `artifact_urls`

Important UI rule:

- Display `status` and `audit_gate_status` separately. Execution completion does not mean audit pass.

## Event Strategy
No SSE route exists in the current API. The safe default is polling:

- Start with `after_sequence=0`.
- Store the highest event `sequence` seen.
- Poll `GET /v1/research/jobs/{job_id}/events?after_sequence=<highest_sequence>`.
- Append new events in sequence order.
- Stop or slow polling when `status` is terminal: `completed`, `failed`, or `cancelled`.
- Show polling errors as local API connectivity issues, not job failures, unless the job status also reports failure.

## Job Registry Strategy
No job-list endpoint exists. Phase 21 must use one of these local strategies:

- Store submitted job IDs in browser local storage.
- Provide manual job-id entry.
- Import job IDs from copied URLs.

Do not imply that the backend can enumerate all historical jobs until a list endpoint exists.

## Artifact Contract
Use `artifact_urls` from `PublicJobResponse`. Do not construct local filesystem paths in the UI.

Stable artifact names:

| Artifact | Content type expectation | GUI treatment |
| --- | --- | --- |
| `report.md` | plain text Markdown | Markdown/source viewer. |
| `report.html` | HTML | Preferred human report viewer. |
| `report_bundle.json` | JSON | Authoritative bundle inspector. |
| `claims.json` | JSON | Claims table/detail inspector. |
| `sources.json` | JSON | Sources, citations, and snapshots inspector. |
| `audit_decision.json` | JSON | Audit gate and blocking claims inspector. |
| `trace.jsonl` | NDJSON/plain text | Event trace viewer. |
| `manifest.json` | JSON | Artifact index and integrity view. |
| `review_queue.json` | JSON | Manual review queue view. |
| `claim_graph.json` | JSON | Claim/support/conflict graph source view. |
| `review_actions.jsonl` | NDJSON/plain text | Append-only review action log. |

## Artifact Viewer Defaults
- Use `report.html` for readable report display when it exists.
- Use `report_bundle.json` as the canonical data source for claims/evidence navigation.
- Show missing artifacts as pending/unavailable, not as fatal job failures.
- Keep raw JSON and JSONL accessible for reviewer inspection.
- Never hide blocked critical claims; surface `blocked_critical_claim_count` and `audit_gate_status`.

## Native Benchmark Contract
The GUI benchmark console must present only repo-native deterministic layers in this run:

- `smoke_local`: authoritative merge-safe gate.
- `regression_local`: wider deterministic native regression layer.

Suites:

- `company12`
- `industry12`
- `trusted8`
- `file8`
- `recovery6`

Committed benchmark inputs and outputs:

- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/reports/phase5_local_smoke/RESULTS.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`
- `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`

Bounded local run commands may be exposed later:

```bash
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json
uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json
```

Do not add external benchmark UI in the GUI run.

## Recommended Frontend Routes
- `/jobs`: known local jobs and manual job-id loader.
- `/jobs/new`: research submission form.
- `/jobs/:jobId`: status, events, control actions, report, and artifact tabs.
- `/artifacts/:jobId/:artifactName`: focused artifact viewer.
- `/benchmarks`: native benchmark overview.
- `/benchmarks/:suite`: native suite detail.
- `/docs`: local docs/help entrypoints.
- `/settings`: API base URL and local environment notes.

## Safe Action Buttons
Allowed in the first GUI implementation:

- Submit job.
- Refresh job status.
- Start/stop event polling.
- Cancel job.
- Retry job.
- Resume job.
- Refine job.
- Record review action.
- Open artifact URL.
- Copy job ID or local API URL.

Use clear labels that these actions affect the local runtime.

## Known Gaps
- No backend job-list endpoint.
- No SSE endpoint.
- No benchmark API endpoint.
- Desktop wrapper full installer bundling is out of scope for the web GUI contract; bounded Tauri no-bundle build readiness is tracked in `docs/gui/DESKTOP_STATUS.md`.
- No auth, tenant, queue, or object-store surface.
- No production deployment boundary.

## Phase 21 Defaults
- Build under `apps/gui-web/`.
- Use React, TypeScript, Vite, npm, and shadcn/ui-style open-code components.
- Prefer a dense operator/reviewer UI with cards, tables, side/detail panes, and visible evidence/audit/benchmark surfaces.
- Avoid a chat transcript as the primary interface.
