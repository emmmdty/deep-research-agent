# Benchmark Portfolio Preflight Audit

## Summary

This run executed the control-layer benchmark preflight requested by
`.agent/benchmark_portfolio/prompts/00_PREFLIGHT_BENCHMARK_RUN.md`.

Scope stayed within preflight boundaries:
- no worktree was created
- no benchmark adapter/runtime code was added
- no benchmark phase was started

The benchmark control docs exist locally, `BENCHMARK_PLAN_SPEC.yaml` parses,
and the current repository baseline still matches the benchmark spec's native
eval/release assumptions. The run is still blocked from starting benchmark
integration phases because the entire `.agent/benchmark_portfolio/` tree is
currently untracked on `main`, so fresh phase worktrees created from `main`
would not contain the benchmark runbook they are supposed to execute.

## Checked Control Files

- `AGENTS.md`
- `.agent/benchmark_portfolio/AGENTS_OVERLAY.md`
- `.agent/context/PROJECT_SPEC.md`
- `.agent/context/TASK2_SPEC.yaml`
- `.agent/PREFLIGHT_DOC_AUDIT.md`
- `.agent/STATUS.md`
- `FINAL_CHANGE_REPORT.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `docs/final/VALUE_SCORECARD.md`
- `evals/reports/phase5_local_smoke/release_manifest.json`
- `.agent/benchmark_portfolio/BENCHMARK_SPEC.md`
- `.agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml`
- `.agent/benchmark_portfolio/PHASE_PLAN.md`
- `.agent/benchmark_portfolio/IMPLEMENT.md`
- `.agent/benchmark_portfolio/STATUS.md`
- `.agent/benchmark_portfolio/phases/10_phase10_scaffolding_and_facts.md`
- `.agent/benchmark_portfolio/phases/11_phase11_longfact_safe.md`
- `.agent/benchmark_portfolio/phases/12_phase12_longbench_v2.md`
- `.agent/benchmark_portfolio/phases/13_phase13_browsecomp_and_gaia.md`
- `.agent/benchmark_portfolio/phases/14_phase14_portfolio_docs_and_gate.md`

## Validation Evidence

- `BENCHMARK_PLAN_SPEC.yaml` parsed successfully via:
  `UV_CACHE_DIR=/tmp/uv-cache uv run python -c 'from pathlib import Path; import yaml; yaml.safe_load(Path(".agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml").read_text()); print("BENCHMARK_PLAN_SPEC_OK")'`
- `main.py --help` confirms the native CLI/eval surface is still present.
- `evals/reports/phase5_local_smoke/release_manifest.json` exists and reflects a
  passed native release gate.
- `docs/final/VALUE_SCORECARD.md` and
  `evals/reports/followup_metrics/*` exist, so the benchmark spec's assumed
  post-Phase-6 baseline is still present.
- Native eval assets still exist:
  - `evals/suites/company12.yaml`
  - `evals/suites/industry12.yaml`
  - `evals/suites/trusted8.yaml`
  - `evals/suites/file8.yaml`
  - `evals/suites/recovery6.yaml`
  - `scripts/run_local_release_smoke.py`
  - `scripts/run_value_metrics.py`
  - `scripts/run_value_ablation_pack.py`
  - `scripts/build_value_scorecard.py`

## Findings

### 1. Benchmark control docs exist locally

All required benchmark control-layer docs requested by the preflight prompt are
present in the workspace.

The directory also contains `:Zone.Identifier` sidecar files. Those are ignored
Windows metadata artifacts and are not part of the benchmark control-layer
contract.

### 2. The benchmark plan spec is syntactically valid

`.agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml` parsed as valid YAML.

### 3. The repo baseline matches the benchmark spec assumptions

The benchmark spec assumes a completed native deep-research baseline with:
- deterministic native evals
- authoritative local release smoke
- follow-up metrics/value scorecard artifacts
- CLI/eval entrypoints on `main`

The current repo still matches those assumptions:
- `main.py` exposes the native `eval` subcommand
- the authoritative native suites remain `company12`, `industry12`, `trusted8`,
  `file8`, and `recovery6`
- `evals/reports/phase5_local_smoke/release_manifest.json` exists
- `docs/final/EXPERIMENT_SUMMARY.md` and `docs/final/VALUE_SCORECARD.md` still
  describe the native release gate as authoritative

### 4. Existing doc layers have manageable but real boundary ambiguity

These are not hard blockers by themselves, but they should be carried forward
explicitly in Phase 10 implementation notes:

- Root `AGENTS.md` points the active run loop at `.agent/STATUS.md` and
  `.agent/phases/*`, while the benchmark runbook uses
  `.agent/benchmark_portfolio/STATUS.md` and
  `.agent/benchmark_portfolio/phases/*`.
- Root source-of-truth language centers `.agent/context/*`, while the benchmark
  overlay centers benchmark plan docs. The safe reading is:
  `.agent/context/*` remains the product/runtime contract, and
  `.agent/benchmark_portfolio/*` governs eval-layer benchmark expansion only.
- The repo still carries legacy benchmark/comparator diagnostics under
  `evals/legacy_diagnostics/` and scripts such as `scripts/run_benchmark.py`,
  `scripts/full_comparison.py`, and `scripts/run_portfolio12_release.py`.
  Phase 10 must treat those as legacy diagnostics, not as the new external
  benchmark substrate.

### 5. Hard blocker: benchmark control layer is not tracked on `main`

This is the decisive preflight blocker.

Evidence:
- `git status --short` reports `?? .agent/benchmark_portfolio/`
- `git ls-files .agent/benchmark_portfolio` returns no tracked files
- `git check-ignore -v ...` does not report these files as ignored

Operational consequence:
- the benchmark runbook requires creating fresh linked worktrees from `main`
- those worktrees would not include `.agent/benchmark_portfolio/*`
- Phase 10-14 would therefore start without the control files they depend on

## Conflicts And Compatibility Notes

- No conflict was found with the benchmark claim that the native custom
  benchmark remains the authoritative release gate; this matches
  `FINAL_CHANGE_REPORT.md`, `docs/final/EXPERIMENT_SUMMARY.md`,
  `docs/final/VALUE_SCORECARD.md`, and the native release manifest.
- No conflict was found with the benchmark plan's assumption that benchmark
  logic should stay outside the main runtime path; the existing eval layout
  already separates `src/deep_research_agent/evals/` and `evals/`.
- The benchmark runbook's clean-baseline assumption does conflict with current
  repo state because `.agent/benchmark_portfolio/` is still untracked.

## Required Next Manual Action

Track and commit the full `.agent/benchmark_portfolio/` control layer on the
starting branch, then rerun this preflight before launching
`START_BENCHMARK_INTEGRATION_RUN.md`.

NOT_READY
