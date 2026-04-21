# Metric Definitions

## Scope

Phase 7 adds a reproducible follow-up value-metrics pack on top of the committed
Phase 5 local smoke artifacts and optional fresh measured reruns.

Outputs:

- `evals/reports/followup_metrics/headline_metrics.json`
- `evals/reports/followup_metrics/value_dashboard.json`
- `evals/reports/followup_metrics/stage_timing_breakdown.json`

## Core Formulas

- `completion_rate = completed_jobs / total_jobs`
- `bundle_emission_rate = jobs_with_bundle / completed_jobs`
- `audit_pass_rate = jobs_with_audit_gate_passed / completed_jobs`
- `critical_claim_support_precision = supported_critical_claims / total_critical_claims`
- `citation_error_rate = blocked_or_unsupported_critical_claims / total_critical_claims`
- `provenance_completeness = provenance_complete_points / provenance_points_checked`
- `policy_compliance_rate = policy_compliant_source_accesses / source_accesses_checked`
- `trusted_only_success_rate = completed_trusted_only_jobs / trusted_only_jobs`
- `file_input_success_rate = ingested_file_sources / declared_file_inputs`
- `conflict_detection_recall = detected_conflict_sets / expected_conflict_sets`
- `source_count_per_job = mean(source_count)`
- `evidence_count_per_job = mean(evidence_fragment_count)`
- `claim_count_per_job = mean(claim_count)`

## Reliability Metrics

These are imported from the deterministic `recovery6` suite:

- `cancel_success_rate`
- `retry_success_rate`
- `resume_success_rate`
- `refine_success_rate`
- `stale_recovery_success_rate`
- `idle_skip_rate`

## Efficiency Metrics

### Timings

Fresh measured reruns can emit `runtime_metrics.json` per task. When present:

- `ttff_seconds = first_stage_completed_timestamp - job_created_timestamp`
- `ttfr_seconds = bundle_emitted_timestamp - job_created_timestamp`
- `stage_runtime_seconds[stage] = stage_completed_timestamp - stage_started_timestamp`

Headline latency fields are reported as `p50` and `p95` over measured jobs.

When only committed frozen artifacts are available, timing fields are emitted as
`null` with reason `frozen_artifact_timestamps`.

### Tokens and Cost

- `prompt_tokens_per_completed_job = mean(prompt_tokens)`
- `completion_tokens_per_completed_job = mean(completion_tokens)`

If the evaluated jobs are provider-free fixture runs, token counts are `0` and
`estimated_api_cost_per_completed_job` is `null` with reason
`provider_free_fixture_run`.

## Output Conventions

Each headline metric is emitted as an object with:

- `value`
- `sample_size`
- `reason`

`reason` is `null` when the metric was computed directly. When a metric is not
available, `value` is `null` and `reason` explains why.
