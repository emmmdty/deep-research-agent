# Phase 20 — GUI preflight and contract freeze

## Objective
Audit the current local API, artifact contracts, native benchmark surfaces, and docs so the GUI implementation starts from a frozen contract.

## Required outputs
- `.agent/gui_app/GUI_BACKLOG.md`
- updated `.agent/gui_app/STATUS.md`
- `docs/gui/GUI_CONTRACT.md`

## Must determine
- which API endpoints already exist and are stable
- which actions still require CLI fallback
- which job/artifact states need UI support first
- whether SSE/events are available or polling is the safe default
- whether Tauri prerequisites exist locally

## Acceptance
- GUI backlog exists
- GUI contract doc exists
- endpoint/artifact map exists
- explicit decision recorded: web-first + desktop-wrapper later

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- one API smoke test already present in repo
- bounded inspection of bundle/report artifacts
