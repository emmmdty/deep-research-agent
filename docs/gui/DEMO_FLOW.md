# GUI Demo Flow

This flow demonstrates the local web GUI without requiring provider-backed live research or long-running benchmark execution.

## Preconditions

- Node and npm are available.
- Python dependencies can be resolved with `uv`.
- `.env` exists if provider-backed live commands are used.
- Rust/Cargo are only required for the optional Tauri desktop wrapper.

## 1. Verify The Backend Boundary

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts
```

Expected result:

- CLI help prints supported commands.
- API smoke passes.

## 2. Start The Local API

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn deep_research_agent.gateway.api:app --host 127.0.0.1 --port 8000
```

## 3. Start The GUI

```bash
cd apps/gui-web
npm install
npm run dev
```

## 4. Submit A Bounded Job

In the GUI:

1. Open the Jobs area.
2. Enter `Anthropic company profile`.
3. Select `company_trusted`.
4. Click `Submit local job`.

Expected result:

- The request uses `start_worker=false`.
- A job id appears in Known Jobs and Job detail.
- Status and audit gate fields are visible.

## 5. Load Events And Bundle

1. Paste a job id into `Manual job id`.
2. Click `Load job`.
3. Confirm event rows are visible when the backend has emitted events.
4. Click `Load bundle`.

Expected result:

- The GUI calls `/events?after_sequence=0`.
- The bundle inspector shows raw JSON when a bundle exists.
- Report HTML link opens through the API artifact URL when available.

## 6. Review Benchmarks

Open Benchmark console and confirm:

- `smoke_local` is shown as the authoritative merge gate.
- `regression_local` is shown as reviewer-facing wider coverage.
- `company12`, `industry12`, `trusted8`, `file8`, and `recovery6` are visible.
- Native scorecard, casebook, and manifest links are visible.

## 7. Desktop Handoff

Desktop status is `READY_FOR_TAURI_BUILD`. The bounded desktop validation wraps the same web GUI and avoids provider-backed live work:

```bash
npm_config_cache=/tmp/npm-cache npm install --prefix apps/desktop-tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix apps/desktop-tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix apps/desktop-tauri
```

See `docs/gui/DESKTOP_STATUS.md`, `docs/gui/TAURI_UNBLOCK_REPORT.md`, and `apps/desktop-tauri/README.md`.
