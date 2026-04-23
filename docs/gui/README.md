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
Phase 21 establishes the shell, navigation, styling foundation, API URL helpers, and local docs. Research-job forms, artifact inspectors, and benchmark views are implemented in later GUI phases.
