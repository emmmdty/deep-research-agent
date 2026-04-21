# Phase 7 — Metrics instrumentation

## Objective
Make the repository produce explicit, machine-readable headline metrics and stage timings from both:
1. the existing committed smoke outputs
2. at least one fresh rerun

This phase is about instrumentation and aggregation, not about major architectural redesign.

## Required outcomes
- codified metric formulas
- metric aggregation code
- stage timing extraction
- token/cost extraction where available
- headline metrics json
- value dashboard json
- metric definition documentation

## Must produce
At minimum:

- `src/deep_research_agent/evals/value_metrics.py` or equivalent canonical module
- `scripts/run_value_metrics.py`
- `docs/final/METRIC_DEFINITIONS.md`
- `evals/reports/followup_metrics/headline_metrics.json`
- `evals/reports/followup_metrics/value_dashboard.json`
- `evals/reports/followup_metrics/stage_timing_breakdown.json`
- tests for metric aggregation/parsing

## Required metric coverage
This phase must produce code and outputs for:
- delivery metrics
- grounding metrics
- policy metrics
- reliability metrics
- file/cross-source metrics
- stage timings
- token usage
- cost if available, otherwise explicit `null` plus reason

## Constraints
- do not invent data
- do not hard-code hand-written numbers into the final outputs
- if existing artifacts are missing required fields, extend the pipeline or add a parser and document the fallback logic
- keep metric outputs deterministic when rerun against the same artifact root

## Suggested implementation steps
1. Inspect current eval/result artifact schemas
2. Define a canonical value-metrics schema
3. Implement metric extractors from:
   - release manifest
   - suite summaries
   - bundle manifests
   - runtime traces if needed
4. Add stage-timing extraction from runtime events or traces
5. Add token/cost aggregation when the data exists
6. Render `headline_metrics.json` and `value_dashboard.json`
7. Document metric definitions

## Acceptance
This phase passes only when:
- a single command can generate the value-metrics pack from the committed smoke outputs
- the command also works after a fresh rerun of at least one suite
- the metric outputs are machine-readable and deterministic on the same path
- `docs/final/METRIC_DEFINITIONS.md` exists and matches the emitted fields
- focused tests pass

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused metric/parser tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --output-root evals/reports/followup_metrics --json`
- one fresh suite rerun, preferably:
  - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root evals/reports/followup_metrics/company12_fresh --capture-runtime-metrics --json`
- rerun the metric command over both the committed smoke root and the fresh root if the implementation supports multiple inputs

## Notes to record
If stage timing or token/cost data is incomplete, record:
- which fields are missing
- whether the pipeline was extended
- whether the final output uses `null`
- what remains for a future server-grade run

Committed Phase 5 smoke bundles use frozen timestamps for deterministic saved artifacts.
Phase 7 therefore needs two timing modes:

- committed smoke inputs: timing fields may be `null` with an explicit frozen-artifact reason
- fresh measured reruns: timing fields should come from an opt-in pre-normalization sidecar
