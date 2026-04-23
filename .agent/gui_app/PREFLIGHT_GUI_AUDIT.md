# GUI Preflight Audit

## Verdict
READY_FOR_WEB_GUI

## Scope
- Run type: GUI/app preflight only.
- Started at: 2026-04-23T10:38:58Z.
- Main repo: `/home/tjk/myProjects/internship-projects/03-deep-research-agent`.
- Main branch: `main`.
- Baseline HEAD: `f93d457`.
- Implementation boundary: no application code changes, no runtime redesign, no worktree creation.

## Controlling Inputs
- `AGENTS.md`
- `.agent/context/PROJECT_SPEC.md`
- `.agent/context/TASK2_SPEC.yaml`
- `.agent/STATUS.md`
- `README.md`
- `FINAL_CHANGE_REPORT.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `docs/benchmarks/native/README.md`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`
- `.agent/gui_app/GUI_APP_SPEC.md`
- `.agent/gui_app/PHASE_PLAN.md`
- `.agent/gui_app/IMPLEMENT.md`
- `.agent/gui_app/STATUS.md`
- `.agent/gui_app/phases/20_phase20_preflight_and_contract.md`

## Safe Checks
| Check | Command | Result |
| --- | --- | --- |
| CLI readiness | `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` | Passed. CLI exposes `submit,status,watch,cancel,retry,resume,refine,bundle,batch,eval,benchmark`. |
| API smoke | `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` | Passed: `1 passed in 1.31s`. |
| OpenAPI inspection | `UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY' ... app.openapi() ... PY` | Passed. API title is `Deep Research Agent API`, version `0.1.0`. |
| Artifact inspection | bounded JSON inspection of smoke/native manifests and one native bundle | Passed. Smoke release gate is `passed`, native regression status is `passed`, sample bundle has `job.status=completed`, `claims=1`, `sources=2`. |
| Frontend tools | `node --version`; `npm --version`; `pnpm --version` | Node `v24.14.0` and npm `11.12.0` are present. `pnpm` is missing. |
| Desktop tools | `rustc --version`; `cargo --version` | Rust/Cargo are missing, so Tauri is not currently build-verifiable. |
| Local-only assets | explicit path check | `.env`, `.env.example`, `.python-version`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr` are present. |
| Git status before edits | `git status --short` | Existing untracked roots: `.agent/gui_app/` and `.agents/`. |

Final post-document validation:

- Required preflight files exist.
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` passed again.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` passed again: `1 passed in 1.88s`.
- Final `git status --short` shows `.agent/gui_app/`, `.agents/`, and `docs/gui/` as untracked roots.

## Local API Readiness
The local FastAPI surface is ready for a web GUI that submits and inspects known jobs.

Stable paths exposed by OpenAPI:

| Method | Path | GUI use |
| --- | --- | --- |
| `POST` | `/v1/research/jobs` | Submit a local research job. |
| `GET` | `/v1/research/jobs/{job_id}` | Load job status and artifact URLs. |
| `GET` | `/v1/research/jobs/{job_id}/events` | Poll append-only job events with `after_sequence`. |
| `POST` | `/v1/research/jobs/{job_id}:cancel` | Request cancellation. |
| `POST` | `/v1/research/jobs/{job_id}:retry` | Create a retry attempt. |
| `POST` | `/v1/research/jobs/{job_id}:resume` | Resume from the latest checkpoint. |
| `POST` | `/v1/research/jobs/{job_id}:refine` | Record a refinement instruction and resume from a safe boundary. |
| `POST` | `/v1/research/jobs/{job_id}:review` | Append a human review action. |
| `GET` | `/v1/research/jobs/{job_id}/bundle` | Load authoritative `report_bundle.json`. |
| `GET` | `/v1/research/jobs/{job_id}/artifacts/{artifact_name}` | Load stable sidecar artifacts by name. |
| `POST` | `/v1/batch/research` | Submit a bounded batch using the same job request contract. |

Important gaps for GUI planning:

- No `GET /v1/research/jobs` list endpoint exists.
- No SSE endpoint exists; polling `events` is the safe default.
- No benchmark API endpoint exists.
- No server-side auth, tenant, remote queue, or object store boundary exists.
- The API is local-only and backed by SQLite/filesystem semantics.

## Artifact and Bundle Readiness
The artifact surface is sufficient for a first web GUI artifact viewer.

Stable artifact names:

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

GUI defaults:

- Treat `report_bundle.json` as the authoritative machine-readable object.
- Prefer `report.html` for the human report viewer when present.
- Show `claims.json`, `sources.json`, `audit_decision.json`, `review_queue.json`, and `claim_graph.json` as structured inspector tabs.
- Show `trace.jsonl` and `review_actions.jsonl` as append-only text/event views.
- Do not expose local filesystem paths as primary UI links; use `artifact_urls` from the public job response.

## Native Benchmark Readiness
The native benchmark surface is ready to browse in the GUI and partially ready for bounded local CLI actions.

Available reviewer artifacts:

- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/reports/phase5_local_smoke/RESULTS.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`
- `docs/benchmarks/native/README.md`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`
- `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`

Benchmark console defaults:

- Show `smoke_local` as the authoritative merge-safe gate.
- Show `regression_local` as deterministic native regression coverage.
- Include suites `company12`, `industry12`, `trusted8`, `file8`, and `recovery6`.
- Keep external benchmark integration out of scope.
- If run buttons are implemented later, label them as local deterministic CLI actions and keep output roots explicit.

## Frontend and Desktop Environment
Web GUI prerequisites are sufficient:

- Node is present: `v24.14.0`.
- npm is present: `11.12.0`.
- No existing `package.json`, `pnpm-lock.yaml`, Vite config, or frontend app was found.

Desktop wrapper prerequisites are not sufficient:

- `rustc` is missing.
- `cargo` is missing.
- Tauri 2 should not be attempted as a validated build in the next phase.
- Desktop work should be deferred until after web GUI stabilization, then scaffolded/documented if Rust/Cargo remain unavailable.

## Decision
- Start Phase 21 as a local web GUI implementation under `apps/gui-web/`.
- Use React, TypeScript, Vite, and an open-code shadcn/ui-style component layer.
- Use npm by default unless the implementation phase intentionally introduces another package manager.
- Use polling for job events.
- Maintain a client-side known-job registry until a backend job-list endpoint is added in a later phase.
- Treat desktop packaging as a later optional wrapper, not a blocker for the web GUI.

## Blockers
- None for web GUI start.

## Non-blocking Risks
- Missing job-list endpoint means first GUI cannot browse all historical jobs without a client-side registry or manual job-id entry.
- Missing benchmark API means Phase 23 must initially browse committed artifacts and use CLI fallback for local run actions.
- Missing Rust/Cargo blocks a validated Tauri build on this machine.
- `.agent/gui_app/` and `.agents/` were already untracked before this preflight; keep that visible in status instead of treating it as a clean main baseline.
