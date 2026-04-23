# Phase 24 — Desktop shell and handoff docs

## Objective
Wrap the GUI as a local app if prerequisites exist; otherwise produce a validated scaffold and explicit docs.

## Required outcomes
- if Tauri prerequisites are present: runnable Tauri wrapper
- if prerequisites are absent: desktop scaffold + docs + blocked note
- `docs/gui/USAGE_GUIDE.zh-CN.md`
- `docs/gui/ARCHITECTURE.md`
- `docs/gui/DEMO_FLOW.md`

## Acceptance
- web GUI is still green
- desktop status is clearly one of: runnable / scaffolded_blocked
- handoff docs exist and are linked from README or docs index

## Validation
Run at least:
- GUI build
- Tauri dev/build smoke if prerequisites are available
- final docs/link checks
- clean git status
