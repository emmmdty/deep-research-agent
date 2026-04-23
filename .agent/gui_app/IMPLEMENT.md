# GUI / App Runbook

## Source of truth order
1. AGENTS.md
2. .agent/context/PROJECT_SPEC.md
3. .agent/context/TASK2_SPEC.yaml
4. .agent/STATUS.md
5. README.md
6. FINAL_CHANGE_REPORT.md
7. docs/final/EXPERIMENT_SUMMARY.md
8. docs/benchmarks/native/README.md
9. docs/benchmarks/native/NATIVE_SCORECARD.md
10. docs/benchmarks/native/CASEBOOK.md
11. .agent/gui_app/GUI_APP_SPEC.md
12. .agent/gui_app/PHASE_PLAN.md
13. .agent/gui_app/STATUS.md
14. active phase file

## Worktree protocol
- verify `main`
- create a fresh linked git worktree and phase branch
- bootstrap local-only assets if needed
- complete only the active phase
- run acceptance checks
- if pass: commit, merge into main, rerun smoke, remove worktree, delete branch, update status
- if fail: stay in the same worktree, revise the phase file, retry
- maximum 4 attempts per phase

## Branch naming
- `codex/phase20-gui-preflight/attempt-1`
- `codex/phase21-web-gui/attempt-1`
- `codex/phase22-job-ux/attempt-1`
- `codex/phase23-benchmark-console/attempt-1`
- `codex/phase24-desktop-handoff/attempt-1`

## Hard rules
- do not redesign runtime or provider layers
- consume the existing local API / CLI surfaces
- do not make external benchmark or provider secrets mandatory
- keep desktop packaging optional but scaffolded if prerequisites are missing
- keep new UI code under app-specific roots, not mixed into `src/deep_research_agent/`

## Expected paths to add
- `apps/gui-web/`
- optionally `apps/gui-desktop/` or `desktop/tauri/`
- GUI docs under `docs/gui/`
- UI screenshots or static assets under `docs/gui/assets/` if generated
