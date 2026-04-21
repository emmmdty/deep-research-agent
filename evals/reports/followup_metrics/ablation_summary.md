# Phase 8 Ablation Summary

| Ablation | Status | Scope | Key delta | Interpretation |
| --- | --- | --- | --- | --- |
| audit_on_vs_off | passed | company12/company-openai-surface | `{"completion_rate": 0.0, "critical_claim_support_precision": 1.0, "unsupported_claim_leakage_rate": 1.0}` | Without audit-grounded support edges, unsupported claim leakage rises while the fixture still completes. |
| strict_source_policy_vs_relaxed | passed | trusted8/trusted-langgraph-brief | `{"bundle_emission_rate": 0.0, "completion_rate": 0.0, "policy_compliance_rate": 0.333}` | Relaxing trusted-only enforcement keeps the bundle flowing but admits a source the strict policy would block. |
| evidence_first_vs_baseline_synthesis | passed | company12/company-openai-surface | `{"citation_error_rate": 1.0, "critical_claim_support_precision": 1.0, "provenance_completeness": 1.0}` | Removing evidence-first grounding erodes provenance and support quality immediately in the emitted bundle. |
| rerank_on_vs_off | passed | industry12/industry-agent-stack | `{"completion_rate": 0.0, "critical_claim_support_precision": 0.5}` | Disabling the rerank-like edge selection leaves a critical claim with only context-only evidence. |
| provider_auto_vs_manual | passed | provider_router | `{"live_latency_delta": null, "live_quality_delta": null}` | Auto-routing can be inspected deterministically, but this local follow-up run does not include live quality or billing comparisons. |
| new_runtime_vs_legacy | not_comparable | runtime_control_plane | `{}` | No like-for-like legacy runtime fixture remains that matches the current deterministic job contracts and bundle outputs. |
