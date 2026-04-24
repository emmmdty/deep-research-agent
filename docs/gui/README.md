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
The local web GUI is the primary operator/reviewer surface. The desktop wrapper under `desktop/tauri/` is now Tauri 2 build-ready for bounded local validation.

## Runbooks
- `docs/gui/JOB_FLOW.md` documents the submit/status/events/bundle flow.
- `docs/gui/BENCHMARK_CONSOLE.md` documents the native benchmark evidence view.
- `docs/gui/USAGE_GUIDE.zh-CN.md` is the Chinese operator guide.
- `docs/gui/ARCHITECTURE.md` documents the GUI architecture boundary.
- `docs/gui/DEMO_FLOW.md` documents the bounded local demo flow.
- `docs/gui/DESKTOP_STATUS.md` records desktop wrapper status.
- `docs/gui/TAURI_UNBLOCK_REPORT.md` records the desktop self-check and unblock run.
