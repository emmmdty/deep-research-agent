# Final Change Report

## Outcome

This repository now implements the target Deep Research Agent shape defined by
`.agent/context/PROJECT_SPEC.md` and `.agent/context/TASK2_SPEC.yaml`.

The supported product boundary is:

- deterministic research job runtime under `src/deep_research_agent/research_jobs/`
- evidence-first connector, snapshot, audit, and report-bundle pipeline
- provider abstraction for OpenAI, Anthropic, and compatible backends
- developer CLI, local HTTP API, batch submission surface, and deterministic eval runner
- release-gated local smoke evidence under `evals/reports/phase5_local_smoke/`

It is not a frontend, not a chat shell, and not a multi-agent-count demo.

## What Changed

### Architecture

- Rebuilt the canonical implementation under `src/deep_research_agent/`.
- Converted `main.py` into a thin wrapper over the supported CLI.
- Promoted runtime, provider routing, connectors, auditor, reporting, gateway, and evals into the canonical package.
- Split lifecycle `status` from `audit_gate_status` and stabilized cancel/retry/resume/refine flows.
- Added claim-centric artifact delivery: `report_bundle.json`, `manifest.json`, `claims.json`, `sources.json`, `trace.jsonl`, `claim_graph.json`, and review sidecars.

### Measured value pack

- Added follow-up value metrics, ablations, and latency/cost summaries under `evals/reports/followup_metrics/`.
- Added the deterministic native regression layer under `evals/reports/native_regression/` with reviewer-facing docs in `docs/benchmarks/native/`.
- Added the reviewer-facing scorecard outputs:
  - `docs/final/VALUE_SCORECARD.md`
  - `docs/final/VALUE_SCORECARD.json`
- Added the native reviewer outputs:
  - `docs/benchmarks/native/README.md`
  - `docs/benchmarks/native/NATIVE_SCORECARD.md`
  - `docs/benchmarks/native/CASEBOOK.md`
- Added a reproducible scorecard generator at `scripts/build_value_scorecard.py`.
- Added reproducible native benchmark builder/runner scripts:
  - `scripts/run_native_regression.py`
  - `scripts/build_native_benchmark_summary.py`
- Made the project story measurable instead of descriptive-only: grounded bundle emission, source-policy/provenance retention, recovery-flow reliability, file-ingest capability, and stage timing now have committed artifacts.
- Preserved the current deployment boundary honestly: the HTTP API is local-only and the repo is not a multi-tenant production SaaS.

### Public surfaces

- Added the supported CLI commands:
  `submit`, `status`, `watch`, `cancel`, `retry`, `resume`, `refine`, `bundle`, `batch run`, and `eval run`.
- Added the local FastAPI surface in `src/deep_research_agent/gateway/api.py`.
- Added batch file submission and stable artifact-name routing.

### Eval and release flow

- Added the canonical local eval stack in `src/deep_research_agent/evals/`.
- Added the root `evals/` tree for suites, datasets, rubrics, committed smoke outputs, and legacy diagnostic notes.
- Added the Phase 5 low-cost release smoke runner in `scripts/run_local_release_smoke.py`.
- Expanded the native/custom benchmark surface with `regression_local` variants for `company12`, `industry12`, `trusted8`, `file8`, and `recovery6`.
- Preserved the current `smoke_local` release smoke pack as the authoritative merge-safe gate while adding a wider deterministic native regression layer.
- Upgraded `configs/release_gate.yaml` and `scripts/release_gate.py` so release proof now requires suite evidence, not benchmark-only diagnostics.
- Normalized saved smoke artifacts so reruns are byte-stable and file-ingest outputs are portable across worktrees and `main`.

## Archived

- `legacy/agents/`
- `legacy/workflows/`
- `evals/legacy_diagnostics/`
- legacy graph-adjacent prompt and skill wrappers are compatibility-only, not the supported execution path

Phase 0 also froze the handling of previously unmapped directories:

- `capabilities/`: split; MCP runtime concerns migrated toward canonical connector ownership, legacy graph routing treated as archive/compatibility material
- `prompts/`: archived with the legacy graph runtime
- `schemas/`: kept and re-scoped as live contract schemas
- `examples/`: re-scoped to current CLI/API/batch demos; legacy example flow is no longer the target product path
- `skills/`: archived as legacy wrappers
- `workspace/`: retained only as a runtime/eval data root, never as source

## Deleted or Replaced

- Replaced the old source-profile names:
  - `open-web` -> `company_broad`
  - `trusted-web` -> `company_trusted`
  - `public-then-private` -> `public_then_private`
- Added new first-class source profiles:
  - `industry_trusted`
  - `industry_broad`
  - `trusted_only`
- Replaced the old pre-Phase-4 “no API” test contract with the implemented local HTTP API surface and corresponding regression tests.

## What Remains

- The HTTP API is local-only and still backed by SQLite, filesystem artifacts, and local subprocess workers.
- There is no auth, tenant isolation, external queue, or object storage indirection layer.
- Manual review writes are append-only and surfaced through events/sidecars, but they do not fully recompile `report_bundle.json`.
- The heavy benchmark/comparator stack remains useful for diagnostics, but it is not the authoritative release gate.
- `legacy-run` remains as a hidden compatibility path only.

These are documented limits, not hidden blockers for the current repository target.

## How To Run The System

### Install

```bash
uv sync --group dev
cp .env.example .env
```

### CLI lifecycle

```bash
uv run python main.py submit --topic "Anthropic company profile" --source-profile company_trusted
uv run python main.py watch --job-id <job_id>
uv run python main.py bundle --job-id <job_id> --json
```

### Local API

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

### Batch

```bash
uv run python main.py batch run --file batch.jsonl --json
```

## How To Reproduce The Key Eval and Demo Flow

### Deterministic local eval

```bash
uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json
uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json
uv run python main.py eval run --suite trusted8 --output-root evals/reports/phase5_local_smoke/trusted8 --json
uv run python main.py eval run --suite file8 --output-root evals/reports/phase5_local_smoke/file8 --json
uv run python main.py eval run --suite recovery6 --output-root evals/reports/phase5_local_smoke/recovery6 --json
```

### Release smoke

```bash
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
```

### Key committed outputs

- `evals/reports/phase5_local_smoke/release_manifest.json`
- `evals/reports/phase5_local_smoke/RESULTS.md`
- `evals/reports/native_regression/release_manifest.json`
- `evals/reports/native_regression/native_summary.json`
- `evals/reports/native_regression/RESULTS.md`
- `evals/reports/phase5_local_smoke/company12/summary.json`
- `evals/reports/phase5_local_smoke/industry12/summary.json`
- `evals/reports/phase5_local_smoke/trusted8/summary.json`
- `evals/reports/phase5_local_smoke/file8/summary.json`
- `evals/reports/phase5_local_smoke/recovery6/summary.json`
- `docs/benchmarks/native/NATIVE_SCORECARD.md`
- `docs/benchmarks/native/CASEBOOK.md`

## Final Verification Snapshot

At the end of Phase 5, `main` passed:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase5_evals.py tests/test_release_gate.py tests/test_release_runner.py tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_cli_runtime.py`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json`
- `git status --short` stayed clean after the release-smoke rerun

The follow-up metrics/value pack adds these review artifacts on top of that baseline:

- `docs/final/VALUE_SCORECARD.md`
- `docs/final/VALUE_SCORECARD.json`
- `evals/reports/followup_metrics/ablation_summary.md`
- `evals/reports/followup_metrics/latency_cost_summary.json`
- `evals/reports/followup_metrics/provider_routing_comparison.json`

## Pointers

- `README.md`
- `docs/architecture.md`
- `docs/development.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `docs/final/VALUE_SCORECARD.md`
- `evals/README.md`
