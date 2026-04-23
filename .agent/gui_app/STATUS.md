# GUI / App Run Status

## Static run info
- run_id: gui-preflight-20260423T103858Z
- main_repo_abs: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_branch: main
- worktrees_root: not used for preflight; prompt explicitly forbids worktree creation
- started_at: 2026-04-23T10:38:58Z
- codex_model: gpt-5.4
- sandbox_mode: danger-full-access
- approval_policy: never

## Current overall status
- current_phase: job_ux
- current_phase_slug: phase22-job-ux
- current_attempt: 1
- last_successful_phase: phase22_job_ux
- overall_state: phase22_job_workspace_completed

## Worktree state
- active_branch: codex/phase22-job-ux/attempt-1
- active_worktree: /home/tjk/myProjects/internship-projects/_codex_worktrees/phase22-job-ux-attempt-1
- main_clean_before_phase: yes after Phase 21 was merged to `main`
- post_merge_smoke_status: pending for Phase 22

## Local-only / ignored asset audit
- checked_paths: `.env`, `.env.example`, `.python-version`, `.venv`, `.codex/config.toml`, `workspace`, `venv_gptr`
- missing_assets: `.env`, `.venv`, `.codex/config.toml`, `workspace`, and `venv_gptr` were missing in fresh GUI worktrees before bootstrap
- recreated_assets: none
- symlinked_assets:
  - `.env` -> `/home/tjk/myProjects/internship-projects/03-deep-research-agent/.env`
  - `.codex/config.toml` -> `/home/tjk/myProjects/internship-projects/03-deep-research-agent/.codex/config.toml`
  - `workspace` -> `/home/tjk/myProjects/internship-projects/03-deep-research-agent/workspace`
  - `venv_gptr` -> `/home/tjk/myProjects/internship-projects/03-deep-research-agent/venv_gptr`
- copied_assets: none
- generated_assets: Phase 22 regenerated a local ignored `.venv` in the worktree via `uv run`
- blockers_from_local_assets: none

## Phase ledger
### Phase 20 - gui_preflight
- status: completed
- attempts: 1
- summary: Local web GUI preflight passed. Existing local FastAPI, artifact, bundle, CLI, and native benchmark surfaces are sufficient to start a web GUI implementation. Desktop/Tauri validation is deferred because Rust/Cargo are missing.
- verdict: READY_FOR_WEB_GUI
- acceptance_checks:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass; CLI exposes `submit,status,watch,cancel,retry,resume,refine,bundle,batch,eval,benchmark`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass (`1 passed in 1.31s`, final rerun `1 passed in 1.88s`)
  - OpenAPI inspection of `deep_research_agent.gateway.api:app` -> pass; API title `Deep Research Agent API`, version `0.1.0`, 11 local paths
  - bounded artifact inspection -> pass; smoke release gate `passed`, native regression status `passed`, sample native bundle `job.status=completed`
  - frontend tool inspection -> Node `v24.14.0`, npm `11.12.0`, `pnpm` missing
  - desktop tool inspection -> `rustc` missing, `cargo` missing
  - required preflight file existence check -> pass
  - final `git status --short` -> `.agent/gui_app/`, `.agents/`, and `docs/gui/` are untracked roots
- artifacts:
  - `.agent/gui_app/PREFLIGHT_GUI_AUDIT.md`
  - `.agent/gui_app/GUI_BACKLOG.md`
  - `docs/gui/GUI_CONTRACT.md`
  - `.agent/gui_app/STATUS.md`
- blockers:
  - none for web GUI start
- notes:
  - Do not create a GUI chat shell; use an operator/reviewer layout.
  - Use polling for job events because no SSE endpoint exists.
  - Use a client-side known-job registry or manual job-id entry because no backend job-list endpoint exists.
  - Native benchmark console should browse committed `smoke_local` and `regression_local` artifacts first.
  - Tauri should wait until the web GUI is stable and Rust/Cargo prerequisites are available or explicitly scaffolded as blocked.

### Phase 21 - web_gui_scaffold
- status: completed
- attempts: 1
- summary: Created the local React + TypeScript + Vite web GUI shell with operator/reviewer navigation, shadcn-style CSS variables/components, typed local API URL helpers, npm scripts, tests, and GUI README.
- acceptance_checks:
  - RED: `npm test` failed before implementation because `./App` and `./api/client` were missing
  - GREEN: `npm test` -> pass (`2` files, `3` tests)
  - `npm run lint` -> pass (`tsc -p tsconfig.json --noEmit`)
  - `npm run build` -> pass (`vite build`, output under `apps/gui-web/dist/`)
  - Vite dev smoke on `http://127.0.0.1:5174/` -> pass (`569` bytes fetched)
- artifacts:
  - `apps/gui-web/`
  - `apps/gui-web/package-lock.json`
  - `docs/gui/README.md`
- blockers:
  - none
- notes:
  - npm is the package manager because Node/npm are present and pnpm is missing.
  - The shell intentionally avoids chat UI patterns and keeps Jobs, Artifacts, Benchmarks, Docs, and Settings as first-class areas.

### Phase 22 - job_ux
- status: completed
- attempts: 1
- summary: Added a bounded job workspace to the React GUI. Operators can submit local no-worker research jobs, choose source profiles, load known or manual job ids, poll lifecycle events, open report HTML links, and inspect raw bundle JSON from the existing FastAPI contract.
- acceptance_checks:
  - RED: `npm test` failed before implementation because `Topic` and `Manual job id` controls did not exist
  - GREEN: `npm test` -> pass (`3` files, `5` tests)
  - `npm run lint` -> pass (`tsc -p tsconfig.json --noEmit`)
  - `npm run build` -> pass (`vite build`, output under `apps/gui-web/dist/`)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass (`970` bytes help output)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass (`1 passed in 2.18s`)
- artifacts:
  - `apps/gui-web/src/job-workspace.test.tsx`
  - `apps/gui-web/src/App.tsx`
  - `apps/gui-web/src/api/client.ts`
  - `docs/gui/JOB_FLOW.md`
- blockers:
  - none
- notes:
  - The GUI uses `start_worker=false` for bounded local submission.
  - Job events are loaded with polling-compatible `after_sequence=0` requests because there is no SSE endpoint.
  - Known jobs are stored client-side in `localStorage` because the backend has no list-jobs endpoint.

### Phase 23 - benchmark_console
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

### Phase 24 - desktop_handoff
- status: pending
- attempts: 0
- summary:
- acceptance_checks:
- artifacts:
- blockers:
- notes:

## Decisions log
- [2026-04-23T10:38:58Z] GUI/app preflight started from `.agent/gui_app/prompts/00_PREFLIGHT_GUI_RUN.md`.
- [2026-04-23T10:38:58Z] Preflight prompt overrides normal GUI worktree protocol for this run: no worktree, no implementation, no application code edits.
- [2026-04-23T10:38:58Z] Verdict recorded as `READY_FOR_WEB_GUI`; desktop wrapper is deferred because Rust/Cargo are missing.
