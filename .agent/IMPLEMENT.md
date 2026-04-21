# Implementation Runbook

## Purpose
This file defines exactly how to execute the repo transformation.

## Non-negotiable operating rules
- Follow `.agent/PHASE_PLAN.md` in order.
- Follow the active phase file exactly.
- Keep `.agent/STATUS.md` current at all times.
- Use the current repository state as input, but use `.agent/context/` docs as the target truth.
- Do not wait for user confirmation on routine implementation work.
- Stop only on:
  - missing permissions,
  - missing secrets that cannot be mocked,
  - or 4 failed attempts in the same phase.

## Canonical paths
At startup, detect and record:
- `MAIN_REPO_ABS`: absolute path of the main repo
- `MAIN_BRANCH`: expected to be `main`
- `WORKTREES_ROOT`: default to sibling directory `../_codex_worktrees`
- `RUN_ID`: timestamped identifier for this Codex run

Record them in `.agent/STATUS.md`.

## Command registry
During Phase 0, discover and freeze the command registry:
- lint command
- format check command
- typecheck command if present
- unit test command
- integration test command
- e2e/smoke command
- package/build command if present
- API smoke command
- CLI smoke command
- eval runner command

Write the discovered commands into `.agent/STATUS.md`.
Later phases must reuse these commands unless the repository changes enough to require an update.
If commands change, update `.agent/STATUS.md` and explain why.

## Worktree naming
Use this naming scheme:

- branch: `codex/<phase_slug>/attempt-<N>`
- worktree dir: `<WORKTREES_ROOT>/<phase_slug>-attempt-<N>`

Examples:
- `codex/phase1-structure/attempt-1`
- `../_codex_worktrees/phase1-structure-attempt-1`

## Phase loop
For every phase:

### Step 1: Verify previous phase on main
Before creating a new phase worktree:
- ensure `main` exists
- ensure the main worktree is on `main`
- verify previous accepted phase outputs on `main`
- rerun the previous phase acceptance checks or the minimum smoke subset
- if verification fails, reopen the previous phase instead of advancing

### Step 2: Create a fresh linked worktree
Create a new linked worktree and a new branch from `main`.

Use commands equivalent to:
- create worktrees root if needed
- `git -C "$MAIN_REPO_ABS" worktree add -b "$BRANCH" "$WT_PATH" "$MAIN_BRANCH"`

Record the branch and worktree path in `.agent/STATUS.md`.

### Step 3: Bootstrap the worktree
Immediately after creation:
- enter the worktree
- inspect ignored/local-only files that might be needed
- inspect environment setup files
- inspect local provider config
- inspect test fixtures and eval fixtures
- inspect whether symlinks or caches are expected
- inspect whether `.codex/config.toml` and local tooling assumptions are available

Do not rely on `git status` alone.
Use explicit filesystem inspection when needed.
If something is missing:
- recreate,
- symlink,
- copy from main worktree if safe,
- or mark as blocker.

Record all findings in `.agent/STATUS.md`.

### Step 4: Execute the active phase
Read the active phase file.
Implement only the current phase scope.
If you discover new sub-steps, add them to:
- the active phase file
- `.agent/STATUS.md`
- `.agent/EXECUTION_BACKLOG.md` if it changes future work

### Step 5: Validate the active phase
Run the acceptance commands from the active phase file.
If a command is missing, derive the best available equivalent from the command registry.
Capture:
- commands run
- pass/fail
- short diagnostics
- artifact paths

Store the summary in `.agent/STATUS.md`.

### Step 6A: If validation passes
Do all of the following in order:
1. commit the worktree branch
2. merge branch into `main`
3. rerun the required smoke checks on `main`
4. if post-merge smoke fails, repair it on the same phase branch/worktree, merge the fix back into `main`, and do not continue until `main` is passing again
5. update `.agent/STATUS.md`
6. remove the linked worktree
7. delete the merged branch
8. continue to the next phase

Use clear commit messages such as:
- `phase1: restructure repository boundaries`
- `phase3: implement evidence and audit pipeline`

### Step 6B: If validation fails
Do all of the following:
1. increment the phase attempt count in `.agent/STATUS.md`
2. append failure analysis to the active phase file
3. revise the current phase plan in that same file
4. stay in the same worktree
5. fix the issues
6. rerun validation

Do not create a new worktree for a failed validation retry.

### Step 7: Attempt limit
If the same phase fails 4 times:
- stop the entire run
- leave the current failing worktree intact
- do not merge into `main`
- write a precise blocker report into `.agent/STATUS.md`
- summarize:
  - current phase
  - completed phases
  - failed validations
  - open blockers
  - exact next manual action

## Documentation update rules
As you work, continuously update:
- `.agent/STATUS.md`
- relevant docs under `docs/`
- README when public surface changes
- migration docs when moving/archive/delete decisions are enacted

## Scope control
Do not expand into unrelated refactors.
If a desirable cleanup is outside the active phase:
- record it in `.agent/STATUS.md`
- continue with the current phase

## Final stop condition
Stop only when:
- all phases are completed and merged into `main`, or
- one phase reaches 4 failed attempts and a blocker report is written
