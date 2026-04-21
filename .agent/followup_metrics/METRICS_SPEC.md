# Metrics and Value-Pack Spec

## Baseline
This repository has already completed the main transformation phases.
Do not rerun the full Phase 0–6 architecture migration.
Treat the current `main` branch as the baseline and build a follow-up metrics/value pack on top of it.

Assume the baseline already includes:
- canonical implementation under `src/deep_research_agent/`
- deterministic research job runtime
- evidence-first report bundle pipeline
- provider abstraction
- local CLI/API/batch surfaces
- deterministic local eval suites under `evals/reports/phase5_local_smoke/`
- a passed local release gate manifest

## Objective
Produce explicit, reproducible, inspection-friendly metrics that prove what this Deep Research Agent does well.

This follow-up run must close the current evidence gap in:
- headline value metrics
- ablation results
- latency and cost reporting
- stage timing visibility
- README/final-doc scorecard presentation

## Non-goals
- no new frontend
- no large new architecture rewrite
- no restart of Phase 0–6 unless a blocker forces a narrowly scoped repair
- no fabricated numbers
- no vague “works well” claims without metrics artifacts

## Required final deliverables
The run must produce all of the following:

- `docs/final/METRIC_DEFINITIONS.md`
- `docs/final/VALUE_SCORECARD.md`
- `docs/final/VALUE_SCORECARD.json`
- `evals/reports/followup_metrics/headline_metrics.json`
- `evals/reports/followup_metrics/value_dashboard.json`
- `evals/reports/followup_metrics/ablation_summary.csv`
- `evals/reports/followup_metrics/ablation_summary.md`
- `evals/reports/followup_metrics/latency_cost_summary.json`
- `evals/reports/followup_metrics/stage_timing_breakdown.json`
- `evals/reports/followup_metrics/provider_routing_comparison.json`
- `evals/reports/followup_metrics/README.md`

Update these existing docs as needed:
- `README.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `FINAL_CHANGE_REPORT.md`

## Headline metrics that must exist
Each metric must appear in machine-readable output and in the human-facing scorecard.

### Delivery / usefulness
- `completion_rate`
- `bundle_emission_rate`
- `rubric_coverage`

### Trustworthiness / grounding
- `critical_claim_support_precision`
- `citation_error_rate`
- `provenance_completeness`
- `audit_pass_rate`

### Governance / source control
- `policy_compliance_rate`
- `trusted_only_success_rate`

### Reliability / control plane
- `cancel_success_rate`
- `retry_success_rate`
- `resume_success_rate`
- `refine_success_rate`
- `stale_recovery_success_rate`
- `idle_skip_rate`

### Cross-source / ingest capability
- `file_input_success_rate`
- `conflict_detection_recall`
- `source_count_per_job`
- `evidence_count_per_job`
- `claim_count_per_job`

### Efficiency
- `ttff_seconds_p50`
- `ttff_seconds_p95`
- `ttfr_seconds_p50`
- `ttfr_seconds_p95`
- `stage_runtime_seconds`
- `prompt_tokens_per_completed_job`
- `completion_tokens_per_completed_job`
- `estimated_api_cost_per_completed_job` or `null` with explicit reason

### Comparative value / ablation
- `audit_value_delta`
- `source_policy_value_delta`
- `evidence_first_value_delta`
- `rerank_value_delta`
- `provider_routing_value_delta`
- `new_runtime_value_delta` if a legacy/baseline comparison is still meaningful

## Metric definitions
Implement exact formulas in code and document them in `docs/final/METRIC_DEFINITIONS.md`.

Minimum formulas:

- `completion_rate = completed_jobs / total_jobs`
- `bundle_emission_rate = jobs_with_bundle / completed_jobs`
- `audit_pass_rate = jobs_with_audit_gate_passed / completed_jobs`
- `critical_claim_support_precision = supported_critical_claims / total_critical_claims`
- `citation_error_rate = citation_errors / total_citations_checked`
- `provenance_completeness = provenance_complete_claims / total_claims_checked`
- `policy_compliance_rate = policy_compliant_source_accesses / total_source_accesses_checked`
- `ttff_seconds = first_artifact_or_first_meaningful_status_timestamp - job_created_timestamp`
- `ttfr_seconds = final_bundle_timestamp - job_created_timestamp`

## Required interpretation layer
The final scorecard must not merely print numbers.
For each headline metric, explain:

- what it measures
- why it matters for a Deep Research Agent
- what failure would look like
- what the current repository achieved

## Target thresholds for the follow-up run
These thresholds are for the follow-up value pack acceptance, not a claim of production-scale guarantees.

- `completion_rate >= 0.95`
- `bundle_emission_rate = 1.0`
- `critical_claim_support_precision >= 0.85`
- `citation_error_rate <= 0.05`
- `provenance_completeness >= 0.95`
- `policy_compliance_rate = 1.0` in trusted/restricted suites
- `resume_success_rate >= 0.95`
- `stale_recovery_success_rate >= 0.95`
- `file_input_success_rate = 1.0`
- `conflict_detection_recall >= 0.80` where the suite defines conflicts

For latency and cost:
- always report the measured values
- do not fail the entire run solely on latency/cost unless the phase file explicitly says so
- if a cost cannot be computed because live provider billing is unavailable, record token counts and set cost to `null` with reason

## Required ablations
Run or honestly skip with documented reason:

1. audit on vs audit off
2. strict source policy vs relaxed source policy
3. evidence-first synthesis vs baseline synthesis
4. rerank on vs rerank off
5. provider auto-routing vs pinned single-provider/manual routing
6. new runtime vs legacy/runtime-diagnostic baseline if still comparable

If one ablation is impossible because the compared component no longer exists as a runnable path, implement the harness, mark it `not_comparable`, and explain why in `ablation_summary.md`.

## Final message this run must support
By the end of this follow-up run, the repository must be able to prove the following with artifacts:

- it completes deep-research jobs reliably
- it produces evidence-first, grounded report bundles
- it enforces source policy
- it survives cancel/retry/resume/stale-recovery flows
- it handles file ingest and cross-source synthesis
- its current architecture is measurably better than weaker baseline modes on the metrics that matter
