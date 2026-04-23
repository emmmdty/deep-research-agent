Treat AGENTS.md as the controlling instruction layer.

This run is a GUI/app preflight only.
Do NOT start implementation.
Do NOT create worktrees.
Do NOT modify application code in this run.

Goal:
Determine whether the current repository is ready to start a GUI/app implementation run on top of the existing local Deep Research Agent baseline.

Read in order:
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
13. .agent/gui_app/IMPLEMENT.md
14. .agent/gui_app/STATUS.md

Audit:
- local API readiness for GUI consumption
- artifact/report/bundle paths needed by a GUI
- native benchmark surfaces needed by a benchmark console
- local environment readiness for frontend work
- optional Tauri prerequisite readiness

Create/update:
- `.agent/gui_app/PREFLIGHT_GUI_AUDIT.md`
- `.agent/gui_app/STATUS.md`

Run only safe checks.
At minimum:
- inspect current docs and repo tree
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- one bounded API smoke test already available in repo
- if safe, inspect whether node/npm/pnpm and rust/cargo are present
- `git status --short`

Return exactly one verdict:
- READY_FOR_WEB_GUI
- READY_FOR_WEB_GUI_AND_DESKTOP_SCAFFOLD
- NOT_READY

Stop after the preflight audit is complete.
