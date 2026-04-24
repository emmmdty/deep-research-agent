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
- current_phase: tauri_desktop_unblock_check
- current_phase_slug: tauri-desktop-unblock
- current_attempt: 1
- last_successful_phase: phase24_desktop_handoff
- overall_state: tauri_desktop_ready_for_bounded_build

## Worktree state
- active_branch: main
- active_worktree: /home/tjk/myProjects/internship-projects/03-deep-research-agent
- main_clean_before_phase: yes before the Tauri unblock check
- post_merge_smoke_status: pending; Git metadata was read-only during branch/worktree creation attempts

## Tauri desktop unblock run - 2026-04-23
- run_id: gui-tauri-unblock-20260423T130834Z
- status: completed locally; final commit may require writable Git metadata
- final_verdict: `READY_FOR_TAURI_BUILD`
- scope: Tauri desktop self-check and repo-local unblock only; no new GUI feature, runtime, benchmark, provider, or backend architecture work
- worktree_attempts:
  - `git worktree add /tmp/tauri-desktop-unblock-attempt-1 -b codex/tauri-desktop-unblock/attempt-1 main` -> failed because Git could not create nested branch refs
  - `git worktree add /tmp/tauri-desktop-unblock-attempt-1 -b tauri-desktop-unblock-attempt-1 main` -> failed because `.git/refs/heads/*.lock` is on a read-only filesystem
  - decision: proceed main-only because the repository was clean, the user allowed bounded main-only maintenance, and Git metadata prevented branch creation
- toolchain:
  - `rustc -V` -> `rustc 1.95.0 (59807616e 2026-04-14)`
  - `cargo -V` -> `cargo 1.95.0 (f2d3ce0bd 2026-03-21)`
  - `node -v` -> `v24.14.0`
  - `npm -v` -> `11.12.0`
- linux_prerequisites:
  - WebKitGTK 4.1, OpenSSL, Ayatana appindicator, GTK 3, JavaScriptCoreGTK 4.1, libsoup 3, and librsvg were visible
  - `pkg-config --modversion xdo` failed, but `libxdo-dev 1:3.20160805.1-4` is installed and Tauri build passed
- repo_local_fixes:
  - added Tauri 2 wrapper under `desktop/tauri/src-tauri/`
  - added `desktop/tauri/package.json` and lockfile with repo-local `@tauri-apps/cli@2.10.1`
  - added `desktop/tauri/src-tauri/icons/icon.png`
  - added `scripts/check_tauri_env.sh`
  - updated `.gitignore`, `docs/gui/DESKTOP_STATUS.md`, `docs/gui/TAURI_UNBLOCK_REPORT.md`, and `desktop/tauri/README.md`
- validation:
  - `./scripts/check_tauri_env.sh` -> pass, `TAURI_ENV_STATUS=ok`
  - `npm_config_cache=/tmp/npm-cache npm install --prefix apps/gui-web` -> pass
  - `npm_config_cache=/tmp/npm-cache npm test --prefix apps/gui-web` -> pass (`4` files, `6` tests)
  - `npm_config_cache=/tmp/npm-cache npm run build --prefix apps/gui-web` -> pass
  - `npm_config_cache=/tmp/npm-cache npm install --prefix desktop/tauri` -> pass
  - `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri` -> pass
  - `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri` -> pass, release binary built
  - `timeout 180s env CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run tauri --prefix desktop/tauri -- dev --no-watch --runner true` -> pass, Vite dev server started and no GUI window was launched
- environment_notes:
  - default `/home/tjk/.npm` and `/home/tjk/.cargo` caches are read-only in this environment; use `/tmp` cache overrides for repeatable local commands
  - `.git/index.lock` is on a read-only filesystem; `git add ...` failed, so this run could not create the requested maintenance commit
  - no sudo was used and no system packages were installed
- remaining_tauri_blockers: none for bounded dev/build validation

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
- generated_assets: Phase 22, Phase 23, and Phase 24 regenerated local ignored `.venv` directories in phase worktrees via `uv run`
- blockers_from_local_assets: none

## Phase ledger
### Phase 20 - gui_preflight
- status: completed
- attempts: 1
- summary: Local web GUI preflight passed. Existing local FastAPI, artifact, bundle, CLI, and native benchmark surfaces were sufficient to start a web GUI implementation. Desktop/Tauri validation was deferred at that time and is now superseded by the 2026-04-23 Tauri unblock run above.
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
  - post-merge `main` smoke -> pass (`npm test`, `npm run lint`, `npm run build`, CLI help, and Phase 4 API smoke)
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
- status: completed
- attempts: 1
- summary: Added a native benchmark console to the React GUI. The view exposes the authoritative `smoke_local` merge gate, the `regression_local` reviewer layer, suite coverage for company12/industry12/trusted8/file8/recovery6, key metrics, scorecard/casebook links, manifest links, and selected casebook report/bundle links.
- acceptance_checks:
  - RED: `npm test -- src/benchmark-console.test.tsx` failed because `Benchmark console` did not exist
  - GREEN: `npm test -- src/benchmark-console.test.tsx` -> pass (`1` test)
  - `npm test` -> pass (`4` files, `6` tests)
  - `npm run lint` -> pass (`tsc -p tsconfig.json --noEmit`)
  - `npm run build` -> pass (`vite build`, output under `apps/gui-web/dist/`)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass (`970` bytes help output)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass (`1 passed in 2.28s`)
  - post-merge `main` smoke -> pass (`npm test`, `npm run lint`, `npm run build`, CLI help, and Phase 4 API smoke)
- artifacts:
  - `apps/gui-web/src/benchmark-console.test.tsx`
  - `apps/gui-web/src/benchmarkData.ts`
  - `apps/gui-web/src/App.tsx`
  - `docs/gui/BENCHMARK_CONSOLE.md`
- blockers:
  - none
- notes:
  - The console presents committed deterministic benchmark artifacts; it does not add browser-triggered benchmark orchestration.
  - `smoke_local` remains the authoritative merge-safe gate.
  - `regression_local` is displayed as reviewer-facing wider coverage.

### Phase 24 - desktop_handoff
- status: completed
- attempts: 1
- summary: Added GUI handoff docs, Chinese usage guide, architecture notes, bounded demo flow, desktop status, and a Tauri scaffold location. Its desktop blocker assessment was superseded by the 2026-04-23 Tauri unblock run above.
- acceptance_checks:
  - RED: required file existence check failed before docs/scaffold were added
  - GREEN: required file existence check for `docs/gui/USAGE_GUIDE.zh-CN.md`, `docs/gui/ARCHITECTURE.md`, `docs/gui/DEMO_FLOW.md`, `docs/gui/DESKTOP_STATUS.md`, and `desktop/tauri/README.md` -> pass
  - desktop prerequisite check -> Node/npm present; `rustc` missing; `cargo` missing
  - docs/link grep for GUI and desktop handoff references -> pass
  - `npm test` -> pass (`4` files, `6` tests)
  - `npm run lint` -> pass (`tsc -p tsconfig.json --noEmit`)
  - `npm run build` -> pass (`vite build`, output under `apps/gui-web/dist/`)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass (`970` bytes help output)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts` -> pass (`1 passed in 2.39s`)
  - post-merge `main` smoke -> pass (`npm test`, `npm run lint`, `npm run build`, CLI help, Phase 4 API smoke, and docs file/link checks)
- artifacts:
  - `docs/gui/USAGE_GUIDE.zh-CN.md`
  - `docs/gui/ARCHITECTURE.md`
  - `docs/gui/DEMO_FLOW.md`
  - `docs/gui/DESKTOP_STATUS.md`
  - `desktop/tauri/README.md`
  - `README.md`
  - `docs/DOCS_INDEX.md`
- blockers:
  - Superseded by the 2026-04-23 Tauri unblock run; bounded desktop dev/build validation now passes.
- notes:
  - desktop_status_at_phase24_handoff: superseded by `READY_FOR_TAURI_BUILD`
  - Do not move runtime, provider, audit, benchmark, or artifact logic into Tauri.
  - Tauri 2 generation was completed during the 2026-04-23 unblock run.

## Decisions log
- [2026-04-23T10:38:58Z] GUI/app preflight started from `.agent/gui_app/prompts/00_PREFLIGHT_GUI_RUN.md`.
- [2026-04-23T10:38:58Z] Preflight prompt overrides normal GUI worktree protocol for this run: no worktree, no implementation, no application code edits.
- [2026-04-23T10:38:58Z] Verdict recorded as `READY_FOR_WEB_GUI`; desktop wrapper readiness was deferred at that time and later resolved in the Tauri unblock run.
