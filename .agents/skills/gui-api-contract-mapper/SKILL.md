---
name: gui-api-contract-mapper
description: Use this skill when a task needs to map the existing local FastAPI and CLI surfaces into a frontend-friendly API client, route model, and artifact/view model. Do not use it for backend redesign or benchmark-only work.
---

# gui-api-contract-mapper

## Purpose
Help Codex read the existing local API, CLI help, and artifact contracts and translate them into:
- frontend route/view models
- typed API clients
- polling/event strategies
- stable artifact links

## Use when
- building GUI job lists and job detail pages
- mapping bundle/artifact endpoints to UI
- deciding whether polling or SSE should be used
- normalizing API contracts for React/Tauri frontend code

## Do not use when
- redesigning the runtime
- changing provider architecture
- doing unrelated docs cleanup

## Steps
1. Read current API docs, CLI help, and artifact docs.
2. Produce a compact endpoint/action matrix.
3. Identify required frontend state objects.
4. Identify safe bounded actions for GUI trigger buttons.
5. Prefer typed client modules over ad-hoc fetches.
6. Preserve the local-only API boundary in the UI wording.
