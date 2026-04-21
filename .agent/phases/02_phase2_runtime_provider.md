# Phase 2 — Runtime and provider layer

## Objective
Implement the deterministic runtime core and the provider abstraction before finishing the broader research pipeline.

## Required outcomes
- canonical job model
- canonical event/checkpoint model
- deterministic state transitions
- explicit separation of `status` and `audit_gate_status`
- provider abstraction layer for:
  - OpenAI
  - Anthropic
  - openai-compatible
  - anthropic-compatible
- config/schema/profile foundations
- local profile smoke path

## Must produce
- runtime service code
- provider router code
- provider capability/config models
- test coverage for state transitions and provider config loading
- updated docs if the public invocation path changed

## Constraints
- no fake provider abstraction
- do not hard-code business logic to one SDK
- do not postpone state model cleanup

## Acceptance
This phase passes only when:
- a local smoke path can create and drive a research job lifecycle
- provider configs load for all required provider classes
- manual and automatic provider routing exist
- `status` and `audit_gate_status` are separate in code and tests
- relevant runtime/provider tests pass

## Validation
Run at least:
- runtime unit tests
- provider/config unit tests
- one CLI smoke for create/status/cancel/retry/resume or equivalent
- lint/typecheck on the new modules

## Attempt 1 execution notes

### Scope completed
- promoted the canonical runtime implementation into `src/deep_research_agent/research_jobs/`
- added the canonical provider layer in `src/deep_research_agent/providers/` for `openai`, `anthropic`, `openai_compatible`, and `anthropic_compatible`
- canonicalized source-profile handling via `src/deep_research_agent/common/source_profiles.py` and new policy profile YAMLs
- updated CLI public commands to `submit`, `status`, `watch`, `cancel`, `retry`, `resume`, and `refine`
- kept legacy import paths alive only as compatibility wrappers (`services/research_jobs/*`, `llm/provider.py`)
- updated schemas and public docs to reflect separated lifecycle status vs. audit-gate status

### Runtime decisions captured during execution
- `recover_stale_jobs()` now skips intentionally idle `created` jobs with no worker lease, pid, or heartbeat so `--no-worker` remains deterministic across later CLI calls
- provider package exports are lazy-loaded to avoid the `configs.settings` <-> provider client circular import
- local lifecycle smoke runs override `WORKSPACE_DIR` to an isolated temp directory instead of writing through the shared `workspace/` symlink

### Validation evidence
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase2_jobs.py tests/test_cli_runtime.py` -> pass (`30 passed`)
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase1_structure_rebuild.py tests/test_cli_runtime.py tests/test_phase2_jobs.py tests/test_phase2_providers.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_basic.py tests/test_scripts.py` -> pass (`81 passed`)
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` -> pass
- isolated lifecycle smoke using `WORKSPACE_DIR=$(mktemp -d)` with:
  - `uv run python main.py submit --topic 'Phase2 smoke deterministic lifecycle' --no-worker --json`
  - `uv run python main.py status --job-id <job1> --json`
  - `uv run python main.py cancel --job-id <job1> --json`
  - `uv run python main.py retry --job-id <job1> --no-worker --json`
  - `uv run python main.py resume --job-id <job1> --no-worker --json`
  - `uv run python main.py refine --job-id <job1> --instruction 'Expand competitor coverage.' --no-worker --json`
  - `uv run python main.py status --job-id <job2> --json`
  - final verification under `uv run python` confirmed both jobs kept `worker_pid == null`, `worker_lease_id == null`, and no `job.recovered` events
