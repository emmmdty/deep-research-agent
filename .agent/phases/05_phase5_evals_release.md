# Phase 5 — Tests, evals, release gates

## Objective
Turn the rebuilt system into an evaluable and releasable engineering artifact.

## Required outcomes
- lint/unit/integration/e2e coverage
- reliability tests for cancel/retry/resume/stale recovery
- provider fallback or switching checks
- source policy restriction checks
- file-ingest and long-document checks
- company/industry research eval tasks
- release gate runner/checklist
- experiment artifacts and summaries

## Must produce
- test suite organization matching the new architecture
- eval runners and configs
- at least low-cost/smoke results locally
- heavy eval harnesses and commands prepared if the current machine cannot run all heavy workloads
- results manifests and summaries in docs or experiments outputs

## Constraints
- do not rely only on old benchmark scripts
- do not declare success without artifacts
- if a heavy experiment cannot run here, implement the harness and run the low-cost version

## Acceptance
This phase passes only when:
- relevant tests pass
- at least one company-research and one industry-research task emit report bundles
- reliability scenarios are exercised
- release gate checklist exists and is runnable
- results/manifests are stored

## Validation
Run at least:
- lint
- unit tests
- integration tests
- e2e smoke
- one reliability suite
- one source-policy suite
- one file-ingest suite
- one or more eval tasks with saved outputs

## Execution notes
- Canonical local eval tree: `evals/suites/`, `evals/datasets/`, `evals/rubrics/`, `evals/reports/`
- Canonical runner: `src/deep_research_agent/evals/runner.py`
- Public developer eval entrypoint: `uv run python main.py eval run --suite <name>`
- Low-cost release pack: `uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json`

## Concrete validation commands
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_release_gate.py tests/test_release_runner.py tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite trusted8 --output-root evals/reports/phase5_local_smoke/trusted8 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite file8 --output-root evals/reports/phase5_local_smoke/file8 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --output-root evals/reports/phase5_local_smoke/recovery6 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json`

## Implementation notes
- Added `src/deep_research_agent/evals/` as the canonical deterministic local suite runner.
- Added the root `evals/` tree for suite configs, frozen datasets, rubric metadata, committed smoke outputs, and legacy-diagnostic notes.
- Extended the public developer CLI with `eval run`.
- Upgraded `configs/release_gate.yaml` and `scripts/release_gate.py` so release proof requires suite evidence in addition to runtime/security/docs/API diagnostics.
- Normalized saved suite artifacts into stable relative paths under `evals/reports/phase5_local_smoke/` so the committed manifests remain valid after worktree cleanup.
