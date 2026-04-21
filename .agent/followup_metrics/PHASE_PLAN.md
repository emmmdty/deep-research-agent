# Follow-up Metrics Phase Plan

## Execution order
Run these follow-up phases strictly in order:

7. Metrics instrumentation
8. Ablation and performance pack
9. Value-pack and public scorecard

Do not rerun the old architecture migration phases unless a blocker forces a tightly scoped repair.

## Phase 7 — metrics instrumentation
Goal:
- add or normalize metric emitters, aggregators, and machine-readable outputs
- define metric formulas
- make headline metrics derivable from both fresh runs and committed smoke outputs

Required outputs:
- metric aggregation code
- metric definition doc
- headline metrics json
- stage timing breakdown json
- tests for metric parsing/aggregation

## Phase 8 — ablation and performance
Goal:
- run meaningful ablations and performance measurements
- produce comparative value evidence
- measure latency, stage timing, token usage, and cost when available

Required outputs:
- ablation summary csv and markdown
- latency/cost summary json
- provider routing comparison json
- saved artifacts under `evals/reports/followup_metrics/`

## Phase 9 — value-pack and signoff
Goal:
- turn the measured outputs into a clear final scorecard
- update README and final docs
- make the project’s value legible for interviews, demos, and code review

Required outputs:
- VALUE_SCORECARD.md / json
- README updates
- final summary links from docs/final/EXPERIMENT_SUMMARY.md
- final validation on main