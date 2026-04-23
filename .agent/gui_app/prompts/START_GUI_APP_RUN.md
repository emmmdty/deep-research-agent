Treat AGENTS.md as the base control layer.
Then treat `.agents/skills/` repo skills as optional helper capabilities for this run.

This repository has already completed:
- architecture migration
- native benchmark buildout
- native optimization
- docs/tree hygiene

Do NOT restart earlier phases.
Run only GUI/app phases 20–24.

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
15. .agent/gui_app/phases/20_phase20_preflight_and_contract.md
16. .agent/gui_app/phases/21_phase21_web_shell.md
17. .agent/gui_app/phases/22_phase22_job_flow_and_artifact_viewer.md
18. .agent/gui_app/phases/23_phase23_native_benchmark_console.md
19. .agent/gui_app/phases/24_phase24_desktop_packaging_and_docs.md

Primary strategy:
- build a local web GUI first on top of the existing local API and artifact surfaces
- use React + TypeScript + Vite for the web shell
- use shadcn/ui for the component layer
- only then optionally add a Tauri 2 desktop wrapper if prerequisites are available

Hard boundaries:
- do not redesign the runtime
- do not replace the existing local API with a new backend
- do not add external benchmark integration in this run
- do not require OpenAI or Anthropic secrets
- do not market the result as a production multi-tenant app

Mandatory loop for every phase:
- verify previous accepted baseline on main
- create a fresh linked git worktree and branch
- bootstrap the worktree, explicitly checking ignored/local-only assets if needed
- execute only the current phase scope
- run phase acceptance checks
- if acceptance passes, commit, merge into main, rerun required main smoke, remove worktree, delete branch, update `.agent/gui_app/STATUS.md`, and continue
- if acceptance fails, stay in the same phase worktree, revise the current phase file with failure analysis and a revised plan, update STATUS, repair, retry
- maximum 4 attempts per phase
- if any phase fails 4 times, stop the run and report blockers precisely

Preferred output paths:
- `apps/gui-web/`
- optional `apps/gui-desktop/` or `desktop/tauri/`
- `docs/gui/`

Required end-state:
- runnable local web GUI
- GUI supports submit/status/report/bundle flows
- GUI surfaces native benchmark layers and artifacts
- desktop wrapper is either runnable or explicitly scaffolded with blocker docs
- GUI docs exist and are linked

Print continuously:
- current phase
- why it matters
- files changed
- commands run
- pass/fail results
- what remains

Start now with Phase 20.
