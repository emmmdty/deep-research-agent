# GUI / App Spec

## Current repo baseline
The repository already has:
- canonical implementation under `src/deep_research_agent/`
- deterministic runtime and local HTTP API
- native benchmark layers (`smoke_local`, `regression_local`)
- reviewer-facing docs and benchmark artifacts

This run adds a graphical interface on top of the existing local system.
It is not a runtime rewrite.

## Product goal
Build a reviewer-friendly and operator-friendly GUI for the local Deep Research Agent.

## Recommended delivery order
1. Local web GUI first
2. Desktop shell second

## Chosen UI strategy
Primary UI:
- `apps/gui-web/`
- React + TypeScript + Vite
- shadcn/ui based component layer

Optional desktop shell:
- `apps/gui-desktop/` or `desktop/tauri/`
- Tauri 2 wrapping the same web UI

## Why this stack
- The current repo already has a local HTTP API and does not need another server layer.
- Vite is simple and works well in monorepos and alternative roots.
- shadcn/ui is open-code and easy to customize.
- Tauri 2 can wrap an existing frontend and supports cross-platform desktop packaging.

## Non-goals
- no chat-first UI
- no complex auth
- no multi-tenant SaaS console
- no external benchmark integration in this run
- no provider-backed full native execution in this run

## Must-have GUI features
- job submission form
- source-profile selection
- job list / job status page
- live-ish progress/event view via polling or SSE if already available
- report viewer
- bundle/artifact viewer
- native benchmark console for smoke_local and regression_local
- docs/help entrypoints

## Nice-to-have
- desktop shell with Tauri 2
- export/open artifact folder actions
- benchmark scorecard browser

## Definition of done
- local web GUI runs against the repo's local API
- the main research flow is usable end to end from the GUI
- at least one native benchmark run can be triggered or browsed from the GUI
- GUI docs exist
- if Tauri prerequisites are available, a desktop wrapper is runnable
- if Tauri prerequisites are unavailable, desktop scaffold + docs are still produced without blocking the GUI run
