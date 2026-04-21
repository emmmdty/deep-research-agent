# Deep Research Agent repository instructions

## Read order before doing any implementation
Always read these files in this exact order before changing code:

1. `.agent/context/PROJECT_SPEC.md`
2. `.agent/context/TASK2_SPEC.yaml`
3. `.agent/context/REPO_AUDIT.md`
4. `.agent/context/ARCHITECTURE.md`
5. `.agent/context/METHODOLOGY.md`
6. `.agent/context/DIRECTORY_BLUEPRINT.md`
7. `.agent/context/EVAL_AND_GATES.md`
8. `.agent/PHASE_PLAN.md`
9. `.agent/IMPLEMENT.md`
10. `.agent/STATUS.md`
11. The active phase file in `.agent/phases/`

`.agent/context/PROJECT_SPEC_FROM_USER.md` and `.agent/context/TASK1_OUTPUT_FULL.md` are long-form references. Read them when the concise files are insufficient.

## Source of truth
Treat `.agent/context/TASK2_SPEC.yaml` and `.agent/context/PROJECT_SPEC.md` as the primary implementation contract.
If the old repository structure conflicts with these files, follow the docs in `.agent/context/` and archive or delete legacy code as needed.

## Operating mode
This repository is being transformed into an enterprise Deep Research Agent for company/industry research.
This is not a chat shell, not a toy demo, and not a multi-agent-count showcase.

## Autonomy rules
- Do not ask the user for routine confirmation.
- Resolve local ambiguity using the context files and record decisions in `.agent/STATUS.md`.
- Keep diffs scoped to the active phase.
- Update docs continuously, not only at the end.
- Run validation after every meaningful milestone and after every phase.
- Print what you are doing, why, commands run, and outcomes.

## Mandatory phase loop
For each phase, follow this exact loop:

1. Verify the previous successfully merged phase on `main`.
2. Create a fresh linked git worktree and branch for the current phase.
3. Work only inside that phase worktree.
4. Implement the current phase.
5. Run the phase acceptance checks.
6. If the phase passes:
   - commit the phase branch
   - merge it into `main`
   - rerun the required smoke checks on `main`
   - remove the linked worktree
   - delete the merged phase branch
   - update `.agent/STATUS.md`
   - continue to the next phase
7. If the phase fails:
   - do not start a new worktree
   - update the current phase file with failure analysis and a revised plan
   - update `.agent/STATUS.md`
   - stay in the same phase and retry
8. Maximum 4 attempts per phase.
9. If 4 attempts fail in one phase:
   - stop the entire run
   - keep the failing worktree intact
   - report the current phase, blockers, failed validations, and next manual action
   - do not advance to the next phase

## Worktree bootstrap rules
After creating a new worktree, explicitly check whether ignored or local-only files are required for this repo:
- `.env`, `.env.*`
- local config files
- `.python-version`
- `.venv` or local virtualenv pointers
- local caches or indices
- local eval fixtures
- model/provider config
- private test data
- `.codex/` local config

Do not assume that absence in `git status` means the file is irrelevant.
If a required local-only asset is missing in the new worktree, either:
- recreate it,
- symlink it,
- copy it from the main worktree when safe,
- or record it as a blocker.

Record every such action in `.agent/STATUS.md`.

## Quality bar
A phase is not done because files changed.
A phase is done only when:
- the intended architecture boundary is clearer than before,
- the required tests/checks for that phase pass,
- docs are updated to match reality,
- the repository is cleaner, not messier.

## Merge discipline
- Use small, reviewable commits.
- Use a clear phase-scoped commit message.
- Never merge a failing phase into `main`.
- Never leave `main` in a broken state.
