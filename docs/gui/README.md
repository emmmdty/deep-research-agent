# GUI Web Console

The GUI is a local operator/reviewer interface for the Deep Research Agent. It consumes the existing local FastAPI and committed benchmark/artifact surfaces; it does not replace the backend runtime.

## Web App
- Path: `apps/gui-web/`
- Stack: React, TypeScript, Vite, npm
- Local API default: `http://127.0.0.1:8000`

## Commands
```bash
cd apps/gui-web
npm install
npm run dev
npm run lint
npm test
npm run build
```

## Current Phase
Phase 24 completes the local web GUI handoff docs and records desktop packaging status. The web GUI is the runnable surface; Tauri desktop packaging is scaffolded but blocked until Rust/Cargo are available.

## Runbooks
- `docs/gui/JOB_FLOW.md` documents the submit/status/events/bundle flow.
- `docs/gui/BENCHMARK_CONSOLE.md` documents the native benchmark evidence view.
- `docs/gui/USAGE_GUIDE.zh-CN.md` is the Chinese operator guide.
- `docs/gui/ARCHITECTURE.md` documents the GUI architecture boundary.
- `docs/gui/DEMO_FLOW.md` documents the bounded local demo flow.
- `docs/gui/DESKTOP_STATUS.md` records desktop wrapper status.
