# Preflight Native Benchmark Audit

## Summary

This preflight audited only the repository's native/custom benchmark track:
`company12`, `industry12`, `trusted8`, `file8`, and `recovery6`.

The current smoke-local native pack reruns cleanly with the existing local environment.
The repository already contains a reusable native eval substrate: suite definitions,
datasets, rubrics, deterministic suite runner, release-smoke pack, and committed
reference artifacts. The highest supported readiness tier today is
`READY_FOR_NATIVE_REGRESSION_EXPANSION`.

The repo is not yet ready for `READY_FOR_PROVIDER_BACKED_FULL_NATIVE_RUN`. The current
native runner is still fixture-driven rather than a real provider-backed research-job
harness, the native suites only exist as `smoke_local` variants, and provider
configuration readiness is only partial for a live cross-provider native run.

## Checked files and commands

Files reviewed:

- `AGENTS.md`
- `.agent/context/PROJECT_SPEC.md`
- `.agent/context/TASK2_SPEC.yaml`
- `.agent/STATUS.md`
- `README.md`
- `FINAL_CHANGE_REPORT.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/README.md`
- `evals/suites/company12.yaml`
- `evals/suites/industry12.yaml`
- `evals/suites/trusted8.yaml`
- `evals/suites/file8.yaml`
- `evals/suites/recovery6.yaml`
- `configs/release_gate.yaml`
- `configs/settings.py`
- `src/deep_research_agent/evals/runner.py`
- `src/deep_research_agent/providers/models.py`
- `scripts/run_local_release_smoke.py`

Commands run:

- `git status --short --branch`
- `uv --version`
- `cat .python-version`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python --version`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/native_benchmark_preflight/company12 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --output-root /tmp/native_benchmark_preflight/recovery6 --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root /tmp/native_benchmark_preflight/release --json`
- `ls -1 evals/suites`
- `ls -1 policies/source-profiles`
- `ls -1 evals/datasets/files`
- `ls -d .env .env.example .venv workspace`
- masked environment and provider-profile inspection via `uv run python`

Validation notes:

- `main.py --help` passed and exposes `eval` alongside the broader CLI surface.
- Direct native smoke reruns passed for `company12` and `recovery6`.
- The current local release smoke rerun passed under `/tmp/native_benchmark_preflight/release`.
- The primary worktree was already dirty before this preflight. After the `/tmp` reruns,
  `git status --short --branch` matched that pre-existing dirty baseline rather than
  introducing new tracked-state drift from the smoke commands themselves.

## Current native benchmark inventory

Canonical native benchmark entrypoints today:

- `uv run python main.py eval run --suite <suite> --output-root <dir> --json`
- `uv run python scripts/run_local_release_smoke.py --output-root <dir> --json`

Current native suite inventory:

| Suite | Executor | Dataset path | Committed task_count | Current variant |
| --- | --- | --- | ---: | --- |
| `company12` | `research_fixture` | `evals/datasets/company12.smoke.yaml` | 1 | `smoke_local` |
| `industry12` | `research_fixture` | `evals/datasets/industry12.smoke.yaml` | 1 | `smoke_local` |
| `trusted8` | `research_fixture` | `evals/datasets/trusted8.smoke.yaml` | 1 | `smoke_local` |
| `file8` | `research_fixture` | `evals/datasets/file8.smoke.yaml` | 1 | `smoke_local` |
| `recovery6` | `reliability_fixture` | `evals/datasets/recovery6.smoke.yaml` | 6 | `smoke_local` |

Important truth from the committed manifest:

- All five suites are currently represented in the authoritative native release pack.
- The names `company12`, `industry12`, `trusted8`, and `file8` do not currently imply
  12 or 8 committed smoke tasks in this repo snapshot. The committed Phase 5 manifest
  still records one task each for those research suites, while `recovery6` records six
  reliability scenarios.

## Current tier classification by suite

| Suite | Current tier classification | What that means today | Latest evidence |
| --- | --- | --- | --- |
| `company12` | Tier 1, smoke-only | Deterministic local smoke via fixture-backed research eval | Direct `/tmp` rerun passed |
| `industry12` | Tier 1, smoke-only | Deterministic local smoke via fixture-backed research eval | Passed inside `/tmp` release smoke |
| `trusted8` | Tier 1, smoke-only | Deterministic trusted-only smoke via fixture-backed research eval | Passed inside `/tmp` release smoke |
| `file8` | Tier 1, smoke-only | Deterministic file-ingest smoke via fixture-backed research eval | Passed inside `/tmp` release smoke |
| `recovery6` | Tier 1, smoke-only | Deterministic reliability/control-plane smoke via fixture-backed eval | Direct `/tmp` rerun passed |

Overall interpretation:

- Suite-by-suite reality is still Tier 1 because all native suites are `smoke_local` only.
- Repository-level readiness is higher than Tier 1 because there is no critical blocker
  to starting native regression-pack implementation work now.

## Current reusable metrics and artifacts

Reusable native metrics already implemented in the local runner:

- Research-oriented metrics:
  `completion_rate`, `bundle_emission_rate`, `audit_pass_rate`,
  `critical_claim_support_precision`, `citation_error_rate`,
  `provenance_completeness`, `rubric_coverage`, `policy_compliance_rate`,
  `file_input_success_rate`, and `conflict_detection_recall`
- Reliability-oriented metrics:
  `completion_rate`, `cancel_success_rate`, `retry_success_rate`,
  `resume_success_rate`, `refine_success_rate`,
  `stale_recovery_success_rate`, and `idle_skip_rate`

Thresholds already encoded in suite YAML:

- `company12`: completion, bundle emission, audit pass all `>= 1.0`;
  critical-claim support precision `>= 0.85`; citation error `<= 0.05`;
  provenance completeness `>= 0.95`; rubric coverage `>= 0.80`
- `industry12`: same as `company12`, plus `conflict_detection_recall >= 0.80`
- `trusted8`: completion, bundle emission, audit pass `>= 1.0`;
  provenance completeness `>= 0.95`; policy compliance `>= 1.0`
- `file8`: completion, bundle emission, audit pass `>= 1.0`;
  provenance completeness `>= 0.95`; file-input success `>= 1.0`
- `recovery6`: completion, cancel, retry, resume, refine, stale recovery,
  and idle skip all `>= 1.0`

Reusable artifacts already emitted by the native stack:

- suite-level `summary.json`
- suite-level `RESULTS.md`
- task-level `report.md`
- task-level `bundle/report_bundle.json`
- task-level `bundle/manifest.json`
- task-level `bundle/trace.jsonl`
- task-level `bundle/sources.json`
- task-level `audit/claim_graph.json`
- task-level `audit/review_queue.json`
- release-pack-level `release_manifest.json`

Current artifact sufficiency:

- Enough for rerunning and comparing local smoke/native-regression iterations
  without inventing a new artifact contract from scratch.
- Not yet enough for a richer benchmark-level reporting surface comparable to a
  dedicated native regression dashboard or provider-backed experiment summary.

## Configuration and local-asset findings

Local environment and assets found:

- `.env` present
- `.env.example` present
- `.venv` present
- `workspace/` present
- `.python-version` present and set to `3.10`
- `uv` available as `0.10.12`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python --version` resolved to `Python 3.10.12`
- `/tmp/native_benchmark_preflight/...` is writable

Source-profile assets found:

- Canonical profiles present:
  `company_broad`, `company_trusted`, `industry_broad`, `industry_trusted`,
  `public_then_private`, and `trusted_only`
- Legacy aliases also remain present:
  `open-web`, `public-then-private`, and `trusted-web`

File-ingest fixtures found:

- `evals/datasets/files/company_context.md`
- `evals/datasets/files/industry_context.txt`
- `evals/datasets/files/trusted_brief.md`

Masked configuration findings from `.env` and runtime settings:

- Set in `.env`: `LLM_MODEL_NAME`, `LLM_API_KEY`, `LLM_BASE_URL`,
  `SEARCH_BACKEND`, `TAVILY_API_KEY`, `MAX_RESEARCH_LOOPS`,
  `MAX_SEARCH_RESULTS`
- Missing in `.env`: `RESEARCH_PROFILE`, `RESEARCH_CONCURRENCY`,
  `JUDGE_MODEL`, `GPT_RESEARCHER_PYTHON`, `OPEN_DEEP_RESEARCH_COMMAND`,
  `OPEN_DEEP_RESEARCH_REPORT_DIR`
- Resolved provider profiles:
  - `openai`: enabled, API key present, base URL present
  - `openai_compatible`: enabled, API key present, base URL present
  - `anthropic`: enabled but API key absent
  - `anthropic_compatible`: enabled but API key absent and base URL absent
- Default provider profile resolves to `openai_compatible`

Interpretation:

- The current deterministic native smoke path is configuration-ready locally.
- Regression-tier native benchmark implementation can start without waiting on new
  local-only assets.
- Provider-backed full native runs are not fully configuration-ready across the
  declared provider matrix yet.
- `.codex/config.toml` was not treated as a blocker because the current native
  benchmark path does not require it.

## Missing pieces for regression-tier native benchmark

- Only `smoke_local` native datasets are present. There are no native
  `regression`, `full`, or similarly expanded suite variants yet.
- The research suites are still very small in committed task count:
  `company12=1`, `industry12=1`, `trusted8=1`, `file8=1`.
- There is no dedicated native-regression pack runner or native-regression
  summary/report surface separate from the Phase 5 smoke release manifest.
- Current rubrics are reusable, but the task breadth, holdouts, and larger
  task matrices needed for a real regression layer are still absent.
- The current reporting contract is good enough for suite reruns, but not yet
  shaped into a benchmark-level native portfolio summary that compares larger
  runs across task families or provider modes.

## Missing pieces for provider-backed full native benchmark

- The current native runner is deterministic and fixture-backed. It does not
  exercise a real live-provider benchmark harness for native suites today.
- `company12`, `industry12`, `trusted8`, and `file8` currently run through
  `research_fixture`; `recovery6` runs through `reliability_fixture`. That is not
  the same as running real research jobs against live providers.
- There is no dedicated provider-backed native task pack, provider-scoped output
  manifest, or full native reporting surface for live runs.
- Provider configuration readiness is only partial: OpenAI/openai-compatible
  profiles look locally resolvable, but Anthropic-side readiness is incomplete.
- There is no confirmed live native acceptance gate yet for provider-backed
  latency/cost/run-variance behavior on the native suite family.

## Blockers

- No blocker was found for rerunning the current smoke-local native pack.
- No blocker was found for starting native regression-pack implementation work.
- Current blockers to provider-backed full native execution:
  - no provider-backed native harness yet
  - no expanded native full/regression datasets yet
  - no native benchmark-level reporting surface for live runs yet
  - incomplete provider readiness across the declared provider matrix
- Process caution:
  the primary worktree was already dirty before this preflight. That did not block
  the `/tmp` smoke reruns, but it means "repo remains clean" can only be interpreted
  here as "no new tracked-state drift from the `/tmp` rerun commands."

## Recommended next step

Start a native-only implementation run that:

- adds regression-tier variants for `company12`, `industry12`, `trusted8`,
  `file8`, and `recovery6`
- expands native datasets and task counts beyond the current smoke fixtures
- adds a native benchmark summary/reporting surface on top of the existing
  suite summaries and release manifest
- keeps provider-backed full native execution explicitly out of the first pass
  until the harness and provider-readiness gaps are closed

## Readiness verdict

`READY_FOR_NATIVE_REGRESSION_EXPANSION`

Reason:

- the current smoke-local native pack reruns cleanly now
- the repository already has enough native eval substrate and local assets to
  begin native-regression implementation work
- provider-backed full native runs are not yet configuration-ready end to end
