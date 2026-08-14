# Native Optimization Report

## Goal

This report summarizes one optimization cycle only.

- baseline tag: `v0.2.0-native-regression`
- baseline commit: `e7219f1`
- selected target: `industry12_discriminativeness`
- optimization type: benchmark hardening, not runtime tuning and not release-gate policy change

## Why `industry12`

At the baseline, the deterministic native regression layer was saturated:

- all suites passed
- suite-level metrics were effectively maxed out
- there was no meaningful suite-level latency/cost differentiator inside this local deterministic layer

That pushed target selection to the discriminativeness rule.

`industry12` was the weakest candidate because its regression rubric explicitly claimed:

- `uncertainty_honesty`
- `control_plane_and_evidence_separation`
- `conflict_detection_recall`

But the emitted baseline artifacts did not actually stress those dimensions:

- `industry12_conflict_case_count = 0`
- `industry12_multi_claim_task_count = 0`
- `industry12_uncertainty_case_count = 0`
- the casebook did not surface a conflict-aware industry example

So the problem was not "industry12 is failing". The problem was "industry12 is passing too easily to be informative."

## What Changed

The cycle hardened exactly four existing `industry12 regression_local` cases:

- `industry-model-gateway`
- `industry-eval-grounding`
- `industry-observability`
- `industry-governance-policy`

Each case now has:

- explicit multi-claim structure
- explicit `claim_support_edges`
- explicit non-empty `conflict_sets`
- at least one `medium` or `high` uncertainty claim
- report text that names uncertainty or scope tension directly

Additive tooling was also introduced:

- `src/deep_research_agent/evals/native_optimization.py`
- `scripts/build_native_optimization_summary.py`
- `evals/reports/native_optimization/optimization_summary.json`
- `evals/reports/native_optimization/BEFORE_AFTER.md`

Reviewer-facing native docs were updated to match:

- `docs/benchmarks/native/CASEBOOK.md` now keeps `industry-agent-orchestration` and swaps the second industry example to `industry-governance-policy`
- `docs/benchmarks/native/NATIVE_SCORECARD.md` adds a small latest-optimization note

## Before / After

The success condition for this cycle was richer benchmark structure without weakening the gate:

| Metric | Before | After |
| --- | ---: | ---: |
| `industry12_suite_status` | `passed` | `passed` |
| `industry12_task_count` | `12` | `12` |
| `industry12_conflict_case_count` | `0` | `4` |
| `industry12_multi_claim_task_count` | `0` | `4` |
| `industry12_uncertainty_case_count` | `0` | `4` |
| `industry12_casebook_conflict_example_present` | `false` | `true` |

Interpretation:

`industry12` is now materially more discriminative while remaining deterministic, passing, and fixed at the same suite size.

## What Did Not Change

This cycle did not:

- change the runtime/provider contract
- change the CLI/API surface
- change the `phase5_local_smoke` release-gate contract
- add external benchmark logic
- introduce provider-backed full native runs

`smoke_local` remains the authoritative merge-safe gate.

## Remaining Limits

Even after the hardening pass, this native benchmark layer is still intentionally bounded:

- deterministic and repo-local rather than live-web or provider-backed
- better at structural regression than at real-world latency/cost profiling
- reviewer-friendly, but still not a substitute for external blind benchmarks
- focused on this repository's product boundary, not on general leaderboard storytelling

## Where To Look Next

- machine summary: `evals/reports/native_optimization/optimization_summary.json`
- human summary: `evals/reports/native_optimization/BEFORE_AFTER.md`
- reviewer doc entrypoint: `docs/benchmarks/native/README.md`
- Chinese reviewer guide: `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`
