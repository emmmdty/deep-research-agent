# Follow-up Metrics Runbook

## Purpose
This runbook governs the follow-up Codex run that adds explicit metrics, ablations, and value-pack outputs on top of the already-completed main architecture migration.

## Source of truth
Read and follow these in order:
1. `AGENTS.md`
2. `.agent/context/PROJECT_SPEC.md`
3. `.agent/context/TASK2_SPEC.yaml`
4. `.agent/PREFLIGHT_DOC_AUDIT.md`
5. `.agent/STATUS.md`
6. `FINAL_CHANGE_REPORT.md`
7. `docs/final/EXPERIMENT_SUMMARY.md`
8. `evals/reports/phase5_local_smoke/release_manifest.json`
9. `.agent/followup_metrics/METRICS_SPEC.md`
10. `.agent/followup_metrics/PHASE_PLAN.md`
11. `.agent/followup_metrics/STATUS.md`
12. the active file in `.agent/followup_metrics/phases/`

## Operating rules
- Treat the current `main` branch as the accepted baseline.
- Do not rerun or redesign the old migration phases unless a follow-up metrics blocker forces a narrowly scoped fix.
- Keep diffs scoped to the active follow-up phase.
- Update `.agent/followup_metrics/STATUS.md` continuously.
- Do not fabricate metrics, deltas, or claims.
- If a metric cannot be computed, implement the harness and record `null` plus the reason.
- If an ablation comparison is not comparable anymore, record `not_comparable` and explain why.

## Worktree protocol
For each phase:
1. verify the previous accepted baseline on `main`
2. create a fresh linked git worktree and branch
3. bootstrap the worktree, including explicit checks for ignored/local-only assets
4. execute only the active phase
5. validate the phase
6. if pass: commit, merge into `main`, rerun required main smoke, remove worktree, delete branch, continue
7. if fail: stay in the same worktree, revise plan in the active phase file, retry
8. maximum 4 attempts per phase
9. if a phase fails 4 times, stop and write a blocker report

Use standard Git linked-worktree commands.
Never leave the main branch dirty.
Never merge a failing phase.

## Worktree naming
- branch: `codex/phase<NN>-<slug>/attempt-<N>`
- worktree dir: `../_codex_worktrees/phase<NN>-<slug>-attempt-<N>`

## Local-only asset audit
After creating each worktree, explicitly inspect and handle:
- `.env`
- `.env.*`
- `.venv`
- `.codex/config.toml`
- `.python-version`
- `workspace/`
- any local eval fixtures or caches
- provider config files or secrets needed for optional live runs

Do not rely on `git status` alone for ignored files.

## Command registry
Start by importing the command registry from `.agent/STATUS.md`.
If a new command is introduced in this follow-up run, append it to `.agent/followup_metrics/STATUS.md`.

Baseline commands expected to exist:
- lint: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- broad regression slice: reuse the committed Phase 6 slice from `.agent/STATUS.md`
- eval runner: `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json`
- CLI help: `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`

## Validation discipline
Every phase must run:
- lint on touched code
- focused tests for touched modules
- at least one artifact-generation command that proves the phase output is real
- documentation validation: the docs updated by the phase must match the code and generated outputs

## Output discipline
Each phase must write its own artifacts under:
- `evals/reports/followup_metrics/`
- `docs/final/`
- `.agent/followup_metrics/STATUS.md`

## Stop condition
This run ends only when:
- phases 7, 8, and 9 are merged into `main`, or
- one phase reaches 4 failed attempts and a blocker report is written

## Required final result
At completion, the repo must contain a scorecard that makes the agent’s value explicit in measured terms, not just architectural terms.