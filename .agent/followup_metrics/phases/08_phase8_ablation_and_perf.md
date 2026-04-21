# Phase 8 — Ablation and performance pack

## Objective
Produce explicit comparative evidence showing why the current Deep Research Agent architecture matters.

This phase must measure value, not only restate architecture.

## Required ablations
Run these ablations whenever technically possible:

1. audit on vs audit off
2. strict source policy vs relaxed source policy
3. evidence-first synthesis vs baseline synthesis
4. rerank on vs rerank off
5. provider auto-routing vs manual single-provider routing
6. current runtime vs legacy or compatibility diagnostic baseline if still runnable

For any comparison that is no longer runnable:
- implement the comparison harness if practical
- otherwise mark it `not_comparable`
- document precisely why

## Required performance outputs
Produce:
- `evals/reports/followup_metrics/ablation_summary.csv`
- `evals/reports/followup_metrics/ablation_summary.md`
- `evals/reports/followup_metrics/latency_cost_summary.json`
- `evals/reports/followup_metrics/provider_routing_comparison.json`

Optionally also produce:
- `evals/reports/followup_metrics/ablation_raw/`
- `evals/reports/followup_metrics/stage_latency_by_suite.csv`

## Required fields per ablation
Each ablation record must include:
- baseline_mode
- comparison_mode
- task_or_suite
- compared_metrics
- absolute_values
- deltas
- interpretation
- artifact_paths
- status (`passed`, `failed`, `not_comparable`, `blocked`)

## Required value deltas
Compute and explain at least:
- `audit_value_delta`
  - how much unsupported or weakly grounded claim leakage changes
  - whether audit blocks low-support outputs without destroying completion
- `source_policy_value_delta`
  - how policy violations change
  - whether trusted-only still completes and emits bundles
- `evidence_first_value_delta`
  - how provenance completeness, citation error, and support precision change
- `rerank_value_delta`
  - how support precision / coverage / latency change
- `provider_routing_value_delta`
  - quality vs latency/cost tradeoff between auto-routing and pinned routing
- `new_runtime_value_delta`
  - reliability/control-plane improvements if legacy comparison is still meaningful

## Performance requirements
Measure and save:
- `ttff_seconds_p50/p95`
- `ttfr_seconds_p50/p95`
- stage runtime breakdown by stage
- prompt/completion tokens per completed job if available
- estimated API cost per completed job if available
- note whether the numbers are from local smoke only or from live provider-backed runs

## Constraints
- do not fabricate positive deltas
- if an ablation shows no gain or a regression, record that honestly
- do not force a failing comparison to pass by redefining the metric after the run without documenting the change

## Acceptance
This phase passes only when:
- at least 4 ablations are actually executed or honestly marked `not_comparable` with evidence
- at least one latency/cost/performance pack is generated
- the generated summary files are machine-readable and human-readable
- the key value deltas are explicitly computed and explained
- focused tests and lint pass

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused eval/ablation tests
- one command that generates the ablation pack
- one command that generates latency/cost summaries
- one command that compares provider routing modes if that surface exists

## Notes to record
For every ablation:
- what changed
- why that comparison matters
- what metric moved
- whether the result strengthens or weakens the project story