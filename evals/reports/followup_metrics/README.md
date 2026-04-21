# Follow-up Metrics Artifacts

This directory contains the committed follow-up metrics/value-pack outputs used by the public scorecard.

Key artifacts:

- `evals/reports/followup_metrics/headline_metrics.json`
- `evals/reports/followup_metrics/value_dashboard.json`
- `evals/reports/followup_metrics/stage_timing_breakdown.json`
- `evals/reports/followup_metrics/ablation_summary.csv`
- `evals/reports/followup_metrics/ablation_summary.md`
- `evals/reports/followup_metrics/latency_cost_summary.json`
- `evals/reports/followup_metrics/provider_routing_comparison.json`

Reproduction commands:

- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_metrics.py --source-root evals/reports/phase5_local_smoke --output-root evals/reports/followup_metrics --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_value_ablation_pack.py --baseline-root evals/reports/phase5_local_smoke --followup-root evals/reports/followup_metrics --output-root evals/reports/followup_metrics --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_value_scorecard.py --release-manifest evals/reports/phase5_local_smoke/release_manifest.json --metrics-root evals/reports/followup_metrics --docs-root docs/final --metrics-readme evals/reports/followup_metrics/README.md --json`

Public scorecard outputs:

- `docs/final/VALUE_SCORECARD.md`
- `docs/final/VALUE_SCORECARD.json`