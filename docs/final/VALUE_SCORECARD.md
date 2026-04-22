# Value Scorecard

## Current Repository Baseline

- Release gate status: `passed`
- Required checks passed: `11/11`
- Baseline manifest: `evals/reports/phase5_local_smoke/release_manifest.json`
- Follow-up metrics root: `evals/reports/followup_metrics`

## Benchmark Layering

- authoritative release gate: native Phase 5 local smoke pack under `evals/reports/phase5_local_smoke/`
- secondary regression: FACTS Grounding open smoke
- external regression: LongFact / SAFE smoke and LongBench v2 short smoke
- challenge-only: BrowseComp guarded smoke, GAIA supported subset, and LongBench v2 medium/long
- reviewer summary: `evals/external/reports/portfolio_summary/portfolio_summary.json`
- benchmark docs: `docs/benchmarks/PORTFOLIO.md`

## What The Deep Research Agent Does

- Runs deterministic research jobs through planning, collection, extraction, claim auditing, synthesis, and rendering stages.
- Emits reviewable bundle artifacts with report text, sources, claims, audit outputs, and manifest sidecars.
- Supports CLI, batch, and local HTTP API entrypoints over the same runtime contract.

## Why This Is Not A Chat Shell Or Toy Demo

- The output contract is a report bundle, not just console prose.
- Source policy, snapshot provenance, and claim-audit gates are part of the runtime contract.
- Cancel, retry, resume, refine, and stale-recovery flows are measured in deterministic suites.
- The HTTP API is real but explicitly local-only and not marketed as a hosted SaaS surface.

## Headline Metrics

| Metric | Value | Why it matters | Failure would look like |
| --- | --- | --- | --- |
| `completion_rate` | `1` | A research agent that cannot finish jobs cannot be trusted as an execution surface. | Failed or abandoned jobs lower the rate and leave the release manifest unable to pass. |
| `bundle_emission_rate` | `1` | This proves the system produces machine-readable report bundles instead of prose-only output. | Completed jobs without bundles would make downstream review, audit, and delivery unreliable. |
| `critical_claim_support_precision` | `1` | Deep research value depends on whether important claims stay evidence-backed. | Unsupported critical claims slip through with weak or missing grounding. |
| `citation_error_rate` | `0` | Low citation error is the minimum bar for an evidence-first research runtime. | Broken or mismatched citations make the bundle look polished while being unverifiable. |
| `provenance_completeness` | `1` | Provenance is what separates a reviewable research bundle from an untraceable summary. | Snapshot references disappear and reviewers cannot trace claims back to collected evidence. |
| `policy_compliance_rate` | `1` | The agent must respect allowed domains and approved private/public source boundaries. | Forbidden or untrusted sources are admitted without being blocked or flagged. |
| `resume_success_rate` | `1` | Recoverability matters more than single-shot success for long-running research flows. | A failed job cannot be resumed cleanly and forces manual cleanup or data loss. |
| `stale_recovery_success_rate` | `1` | This shows the runtime survives worker interruption instead of silently wedging. | Stale jobs stay stuck and require operators to intervene manually. |
| `file_input_success_rate` | `1` | Real research work often mixes approved private files with public sources. | Private file inputs break the run or lose traceability inside the bundle. |
| `conflict_detection_recall` | `1` | A research agent should surface disagreements instead of flattening them into one narrative. | The report merges contradictory evidence without exposing the conflict to reviewers. |
| `ttff_seconds_p50` | `0.299367` | Fast first feedback matters when operators need evidence that work has actually started. | Long silent starts make the runtime look stalled even when it eventually finishes. |
| `ttfr_seconds_p50` | `1.344091` | This is the closest local measure of end-to-end responsiveness for the current deterministic flow. | Bundles arrive too slowly to make the runtime useful as an interactive research tool. |

## Headline Metric Interpretations

### `completion_rate`

- Measures: Completed jobs divided by total evaluated jobs.
- Why it matters: A research agent that cannot finish jobs cannot be trusted as an execution surface.
- Failure mode: Failed or abandoned jobs lower the rate and leave the release manifest unable to pass.
- Current result: Current result: 1.0 over 10 evaluated sample(s).

### `bundle_emission_rate`

- Measures: Completed research jobs that emitted a report bundle.
- Why it matters: This proves the system produces machine-readable report bundles instead of prose-only output.
- Failure mode: Completed jobs without bundles would make downstream review, audit, and delivery unreliable.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `critical_claim_support_precision`

- Measures: Critical claims backed by grounded support edges.
- Why it matters: Deep research value depends on whether important claims stay evidence-backed.
- Failure mode: Unsupported critical claims slip through with weak or missing grounding.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `citation_error_rate`

- Measures: Citation checks that fail grounding or linkage requirements.
- Why it matters: Low citation error is the minimum bar for an evidence-first research runtime.
- Failure mode: Broken or mismatched citations make the bundle look polished while being unverifiable.
- Current result: Current result: 0.0 over 4 evaluated sample(s).

### `provenance_completeness`

- Measures: Claims, sources, and citations that keep snapshot lineage intact.
- Why it matters: Provenance is what separates a reviewable research bundle from an untraceable summary.
- Failure mode: Snapshot references disappear and reviewers cannot trace claims back to collected evidence.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `policy_compliance_rate`

- Measures: Source accesses that satisfy the configured source-policy contract.
- Why it matters: The agent must respect allowed domains and approved private/public source boundaries.
- Failure mode: Forbidden or untrusted sources are admitted without being blocked or flagged.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `resume_success_rate`

- Measures: Resume attempts that successfully recover the same job.
- Why it matters: Recoverability matters more than single-shot success for long-running research flows.
- Failure mode: A failed job cannot be resumed cleanly and forces manual cleanup or data loss.
- Current result: Current result: 1.0 over 6 evaluated sample(s).

### `stale_recovery_success_rate`

- Measures: Stale-worker recovery scenarios that return the job to a healthy path.
- Why it matters: This shows the runtime survives worker interruption instead of silently wedging.
- Failure mode: Stale jobs stay stuck and require operators to intervene manually.
- Current result: Current result: 1.0 over 6 evaluated sample(s).

### `file_input_success_rate`

- Measures: File-ingest tasks that complete with bundle output and provenance intact.
- Why it matters: Real research work often mixes approved private files with public sources.
- Failure mode: Private file inputs break the run or lose traceability inside the bundle.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `conflict_detection_recall`

- Measures: Defined cross-source conflicts that the bundle identifies.
- Why it matters: A research agent should surface disagreements instead of flattening them into one narrative.
- Failure mode: The report merges contradictory evidence without exposing the conflict to reviewers.
- Current result: Current result: 1.0 over 4 evaluated sample(s).

### `ttff_seconds_p50`

- Measures: Median time-to-first-meaningful artifact in the measured fresh rerun.
- Why it matters: Fast first feedback matters when operators need evidence that work has actually started.
- Failure mode: Long silent starts make the runtime look stalled even when it eventually finishes.
- Current result: Current result: 0.299367 seconds over 1 measured job(s).

### `ttfr_seconds_p50`

- Measures: Median time-to-final-report bundle in the measured fresh rerun.
- Why it matters: This is the closest local measure of end-to-end responsiveness for the current deterministic flow.
- Failure mode: Bundles arrive too slowly to make the runtime useful as an interactive research tool.
- Current result: Current result: 1.344091 seconds over 1 measured job(s).

## Ablation Summary

| Ablation | Status | Key deltas | Interpretation |
| --- | --- | --- | --- |
| `audit_on_vs_off` | `passed` | `{"completion_rate": 0.0, "critical_claim_support_precision": 1.0, "unsupported_claim_leakage_rate": 1.0}` | Without audit-grounded support edges, unsupported claim leakage rises while the fixture still completes. |
| `strict_source_policy_vs_relaxed` | `passed` | `{"bundle_emission_rate": 0.0, "completion_rate": 0.0, "policy_compliance_rate": 0.333}` | Relaxing trusted-only enforcement keeps the bundle flowing but admits a source the strict policy would block. |
| `evidence_first_vs_baseline_synthesis` | `passed` | `{"citation_error_rate": 1.0, "critical_claim_support_precision": 1.0, "provenance_completeness": 1.0}` | Removing evidence-first grounding erodes provenance and support quality immediately in the emitted bundle. |
| `rerank_on_vs_off` | `passed` | `{"completion_rate": 0.0, "critical_claim_support_precision": 0.5}` | Disabling the rerank-like edge selection leaves a critical claim with only context-only evidence. |
| `provider_auto_vs_manual` | `passed` | `{"live_latency_delta": null, "live_quality_delta": null}` | Auto-routing can be inspected deterministically, but this local follow-up run does not include live quality or billing comparisons. |
| `new_runtime_vs_legacy` | `not_comparable` | `{}` | No like-for-like legacy runtime fixture remains that matches the current deterministic job contracts and bundle outputs. |

## Reliability Summary

- `cancel_success_rate` = `1`
- `retry_success_rate` = `1`
- `resume_success_rate` = `1`
- `refine_success_rate` = `1`
- `stale_recovery_success_rate` = `1`
- `idle_skip_rate` = `1`

This agent is not a single-shot script; it survives cancel/retry/resume/stale-recovery flows.

## Source-Policy And Audit Summary

- `policy_compliance_rate` = `1`
- `trusted_only_success_rate` = `1`
- `audit_pass_rate` = `1`
- `critical_claim_support_precision` = `1`
- `citation_error_rate` = `0`
- `provenance_completeness` = `1`

This agent does not just search; it preserves source policy and provenance.

## File-Ingest And Cross-Source Summary

- `file_input_success_rate` = `1`
- `conflict_detection_recall` = `1`
- `source_count_per_job` = `2.5`
- `evidence_count_per_job` = `2.5`
- `claim_count_per_job` = `1.25`

## Latency/Cost Summary

- `ttff_seconds_p50 = 0.299367`
- `ttff_seconds_p95 = 0.299367`
- `ttfr_seconds_p50 = 1.344091`
- `ttfr_seconds_p95 = 1.344091`
- `prompt_tokens_per_completed_job = 0.0`
- `completion_tokens_per_completed_job = 0.0`
- `estimated_api_cost_per_completed_job = None`
- cost note: `provider_free_fixture_run`

Stage timing summary:
- `claim_auditing`: p50=`0.079403`, p95=`0.079403`, avg=`0.079403`
- `clarifying`: p50=`0.075739`, p95=`0.075739`, avg=`0.075739`
- `collecting`: p50=`0.07495`, p95=`0.07495`, avg=`0.07495`
- `extracting`: p50=`0.090291`, p95=`0.090291`, avg=`0.090291`
- `normalizing`: p50=`0.09045`, p95=`0.09045`, avg=`0.09045`
- `planned`: p50=`0.077556`, p95=`0.077556`, avg=`0.077556`
- `rendering`: p50=`0.096602`, p95=`0.096602`, avg=`0.096602`
- `synthesizing`: p50=`0.109364`, p95=`0.109364`, avg=`0.109364`

## Clear Interpretation

- This agent does not just generate prose; it emits grounded report bundles.
- This agent does not just search; it preserves source policy and provenance.
- This agent is not a single-shot script; it survives cancel/retry/resume/stale-recovery flows.
- This architecture is better than weaker baselines on the metrics that matter.
- The strongest measured gains come from audit support edges and evidence-first provenance retention: removing either drops support precision or provenance by 1.0 in the deterministic ablations.
- The rerank-like edge selection also matters: turning it off cuts critical-claim support precision from 1.0 to 0.5 in the industry suite ablation.
- Provider auto-routing is only partially evaluated here: the repo proves route selection logic, but not live latency/quality tradeoffs across paid providers.

## Limits

- The HTTP API is local-only.
- The current repo is not a multi-tenant production SaaS.
- Runtime storage remains SQLite plus filesystem artifacts.
- Auth, tenant isolation, external queueing, and object storage are not implemented.
- Cost remains `null` in the local follow-up pack because the measured rerun used provider-free fixtures.

## Artifact Paths

- `release_manifest`: `evals/reports/phase5_local_smoke/release_manifest.json`
- `headline_metrics`: `evals/reports/followup_metrics/headline_metrics.json`
- `value_dashboard`: `evals/reports/followup_metrics/value_dashboard.json`
- `stage_timing_breakdown`: `evals/reports/followup_metrics/stage_timing_breakdown.json`
- `ablation_summary_csv`: `evals/reports/followup_metrics/ablation_summary.csv`
- `ablation_summary_markdown`: `evals/reports/followup_metrics/ablation_summary.md`
- `latency_cost_summary`: `evals/reports/followup_metrics/latency_cost_summary.json`
- `provider_routing_comparison`: `evals/reports/followup_metrics/provider_routing_comparison.json`
- `metrics_readme`: `evals/reports/followup_metrics/README.md`
- `benchmark_portfolio_summary`: `evals/external/reports/portfolio_summary/portfolio_summary.json`
- `benchmark_portfolio_readme`: `evals/external/reports/portfolio_summary/README.md`
- `benchmark_docs_portfolio`: `docs/benchmarks/PORTFOLIO.md`
- `scorecard_markdown`: `docs/final/VALUE_SCORECARD.md`
- `scorecard_json`: `docs/final/VALUE_SCORECARD.json`
- `experiment_summary`: `docs/final/EXPERIMENT_SUMMARY.md`
- `final_change_report`: `FINAL_CHANGE_REPORT.md`
