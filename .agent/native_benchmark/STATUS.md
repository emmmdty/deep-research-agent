# Native Benchmark Preflight Status

## Implementation run

- implementation_started_at_utc: `2026-04-22T14:29:35Z`
- implementation_branch: `codex/native-regression-expansion/attempt-1`
- implementation_worktree: `/home/tjk/myProjects/internship-projects/_codex_worktrees/native-regression-expansion-attempt-1`
- main_baseline_commit: `6b2739860070f6943bc6dc2ba84951abf319957e`
- main_repo_state_before_worktree: clean
- bootstrap_assets_symlinked:
  - `.env`
  - `.venv`
  - `workspace/`
  - `venv_gptr/`
  - `.codex/config.toml`
- baseline_verification:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/native_plan_baseline/company12 --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root /tmp/native_plan_baseline/release --json` -> pass
  - worktree bootstrap `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help` -> pass
  - worktree bootstrap `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_cli_runtime.py` -> pass (15 passed)
- current_execution_state: implementation and validation passed in phase `native_regression_expansion`
- current_focus: remove bootstrap-only symlinks, merge to `main`, rerun smoke on `main`, and clean up the linked worktree
- produced_outputs:
  - `evals/reports/native_regression/release_manifest.json`
  - `evals/reports/native_regression/native_summary.json`
  - `evals/reports/native_regression/RESULTS.md`
  - `docs/benchmarks/native/README.md`
  - `docs/benchmarks/native/NATIVE_SCORECARD.md`
  - `docs/benchmarks/native/CASEBOOK.md`
- implementation_validation:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_native_regression_pack.py tests/test_cli_runtime.py tests/test_release_gate.py tests/test_release_runner.py` -> pass (24 passed)
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --variant smoke_local --output-root /tmp/native_regression_validation/company12_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --variant regression_local --output-root /tmp/native_regression_validation/company12_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite industry12 --variant regression_local --output-root /tmp/native_regression_validation/industry12_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite trusted8 --variant regression_local --output-root /tmp/native_regression_validation/trusted8_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite file8 --variant regression_local --output-root /tmp/native_regression_validation/file8_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --variant regression_local --output-root /tmp/native_regression_validation/recovery6_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json` -> pass
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json` -> pass

## Run metadata

- recorded_start_time_utc: `2026-04-22T12:18:27Z`
- scope: native benchmark preflight only for `company12`, `industry12`,
  `trusted8`, `file8`, and `recovery6`
- mode: audit only, no worktrees, no implementation, no external benchmark work

## Commands actually run

Primary validation commands:

- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/native_benchmark_preflight/company12 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --output-root /tmp/native_benchmark_preflight/recovery6 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root /tmp/native_benchmark_preflight/release --json`
- `git status --short --branch`

Supporting inspection commands:

- `uv --version`
- `cat .python-version`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python --version`
- `ls -1 evals/suites`
- `ls -1 policies/source-profiles`
- `ls -1 evals/datasets/files`
- `ls -d .env .env.example .venv workspace`
- masked env/provider inspection via `uv run python`

## Output paths used under /tmp

- `/tmp/native_benchmark_preflight/company12`
- `/tmp/native_benchmark_preflight/recovery6`
- `/tmp/native_benchmark_preflight/release`
- `/tmp/native_benchmark_preflight/_writability/probe.txt`

## Suite rerun results

- `company12` direct rerun: passed
  - variant: `smoke_local`
  - task_count: `1`
  - output root: `/tmp/native_benchmark_preflight/company12`
- `recovery6` direct rerun: passed
  - variant: `smoke_local`
  - task_count: `6`
  - output root: `/tmp/native_benchmark_preflight/recovery6`
- full local native release smoke rerun: passed
  - suites: `company12`, `industry12`, `trusted8`, `file8`, `recovery6`
  - release gate: `passed`
  - output root: `/tmp/native_benchmark_preflight/release`

Post-rerun repo-state note:

- The primary worktree was already dirty before this preflight.
- After the `/tmp` reruns and before writing this status file, `git status --short --branch`
  matched that pre-existing dirty baseline rather than introducing new tracked-state
  drift from the smoke commands.

## Local asset findings

- `.env` present
- `.env.example` present
- `.venv` present
- `workspace/` present
- `.python-version=3.10`
- `uv=0.10.12`
- `uv run python=3.10.12`
- canonical source profiles present
- legacy source-profile aliases still present
- local file-ingest fixtures present under `evals/datasets/files/`
- `/tmp/native_benchmark_preflight/...` writable

Masked env findings:

- present: `LLM_MODEL_NAME`, `LLM_API_KEY`, `LLM_BASE_URL`, `SEARCH_BACKEND`,
  `TAVILY_API_KEY`, `MAX_RESEARCH_LOOPS`, `MAX_SEARCH_RESULTS`
- missing: `RESEARCH_PROFILE`, `RESEARCH_CONCURRENCY`, `JUDGE_MODEL`,
  `GPT_RESEARCHER_PYTHON`, `OPEN_DEEP_RESEARCH_COMMAND`,
  `OPEN_DEEP_RESEARCH_REPORT_DIR`

Resolved provider-profile readiness:

- `openai`: enabled, API key present, base URL present
- `openai_compatible`: enabled, API key present, base URL present
- `anthropic`: enabled, API key absent
- `anthropic_compatible`: enabled, API key absent, base URL absent
- default provider profile: `openai_compatible`

## Blockers

- No blocker for rerunning the current smoke-local native pack
- No blocker for starting native regression expansion work
- Blockers for provider-backed full native execution:
  - missing provider-backed native harness
  - missing expanded native regression/full datasets
  - missing native live-run reporting surface
  - incomplete provider readiness across the declared provider set
- Process caution only:
  the main worktree is pre-dirty, so cleanliness could only be checked relative to
  the preflight baseline, not as an absolute clean repository state

## Final readiness verdict

`READY_FOR_NATIVE_REGRESSION_EXPANSION`
