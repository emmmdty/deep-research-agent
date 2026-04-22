# Benchmark Portfolio Summary

The authoritative release gate remains the native Phase 5 local smoke pack (`company12`, `industry12`, `trusted8`, `file8`, `recovery6`).

## Current Layering

- authoritative_release_gate: native_phase5_local_smoke
- secondary_regression: facts_grounding_open_smoke
- external_regression: longfact_safe_smoke, longbench_v2_short_smoke
- challenge_track: browsecomp_guarded_smoke, gaia_supported_subset, longbench_v2_medium_long
- deferred: browsecomp_full_1266, facts_private_submission, fully_measured_provider_routing_live_delta, gaia_full_multimodal, gaia_private_submission, longbench_v2_full_submission, longbench_v2_official_submission

## Current Runs

- `browsecomp_guarded_smoke`: role=`challenge_track`, latest_run_status=`completed`, scope=subset=smoke
- `gaia_supported_subset`: role=`challenge_track`, latest_run_status=`completed`, scope=subset=smoke_supported
- `longbench_v2_medium_smoke`: role=`challenge_track`, latest_run_status=`blocked`, scope=subset=smoke, bucket=medium
- `longbench_v2_short_smoke`: role=`external_regression`, latest_run_status=`completed`, scope=subset=smoke, bucket=short
- `longfact_safe_smoke`: role=`external_regression`, latest_run_status=`completed`, scope=subset=smoke
- `facts_grounding_open_smoke`: role=`secondary_regression`, latest_run_status=`completed`, scope=split=open, subset=smoke

## Notes

- The authoritative release gate remains the native Phase 5 local smoke pack (`company12`, `industry12`, `trusted8`, `file8`, `recovery6`).
- FACTS Grounding is the current secondary regression track; it informs RC-style reporting without replacing the native release decision.
- LongFact / SAFE and LongBench v2 short are external regression tracks. BrowseComp, GAIA, and LongBench v2 medium/long remain informative challenge tracks only.
- This builder scans the reports root for concrete run manifests and overlays them onto the static adapter catalog, so blocked challenge runs are reported without fabricating scores.
