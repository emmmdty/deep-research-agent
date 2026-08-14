# Documentation Index

This is the recommended reading order for GitHub reviewers.

## Fast Path

1. [`README.md`](../README.md) - positioning, architecture, quick run, artifact contract, evaluation summary, limits, and roadmap.
2. [`docs/COMPETITIVE_LANDSCAPE.md`](./COMPETITIVE_LANDSCAPE.md) - evidence-backed market comparison and interview talk track.
3. [`REPO_MAP.md`](./REPO_MAP.md) - canonical, active, compatibility, legacy, and local-only boundaries.
4. [`docs/architecture.md`](./architecture.md) - implemented architecture and current limits.
5. [`docs/USER_GUIDE.md`](./USER_GUIDE.md) - 5-minute demo and daily workflows.
6. [`docs/EXPERIMENT_SUMMARY.md`](./EXPERIMENT_SUMMARY.md) - release smoke, native regression, external portfolio, and follow-up metrics summary.
7. [`docs/VALUE_SCORECARD.md`](./VALUE_SCORECARD.md) - measured value pack.
8. [`docs/benchmarks/native/README.md`](./benchmarks/native/README.md) - deterministic native benchmark overview.
9. [`docs/benchmarks/native/NATIVE_SCORECARD.md`](./benchmarks/native/NATIVE_SCORECARD.md) - smoke and regression scorecard.
10. [`docs/gui/README.md`](./gui/README.md) - optional local GUI and desktop docs.

## Engineering Detail

- [`docs/development.md`](./development.md) - local commands, validation, and compatibility notes.
- [`specs/api-readiness-contract.md`](../specs/api-readiness-contract.md) - implemented local HTTP API and batch contract.
- [`specs/evaluation-protocol.md`](../specs/evaluation-protocol.md) - evaluation philosophy and release-gate direction.
- [`docs/adr/`](./adr/) - architecture decision records.

## Benchmark Evidence

- [`evals/reports/live_benchmarks/gaia_real/`](../evals/reports/live_benchmarks/gaia_real/) - real GAIA 2023 validation run (20 Qs) with per-question bundles.
- [`evals/reports/live_benchmarks/browsecomp_real/`](../evals/reports/live_benchmarks/browsecomp_real/) - real BrowseComp run (15 Qs).
- [`evals/reports/live_benchmarks/head_to_head/`](../evals/reports/live_benchmarks/head_to_head/) - ours vs open_deep_research vs gpt-researcher, blind judge.
- [`evals/reports/live_benchmarks/head_to_head_round2/`](../evals/reports/live_benchmarks/head_to_head_round2/) - post-fix re-run: citation_accuracy 0→1.0, source_coverage 0→47-95.
- [`evals/reports/live_benchmarks/gaia_baseline/`](../evals/reports/live_benchmarks/gaia_baseline/) - same-model no-agent control (0/20 vs agent 7/20).
- [`evals/reports/live_benchmarks/cost_analysis/`](../evals/reports/live_benchmarks/cost_analysis/) - cost-per-correct-answer analysis of the committed live lane.
- [`evals/reports/citation_rendering/`](../evals/reports/citation_rendering/) - deterministic inline-citation re-render of all committed live bundles.
- [`docs/ERROR_ANALYSIS.md`](./ERROR_ANALYSIS.md) - failure taxonomy of the live lane.
- [`evals/reports/phase5_local_smoke/release_manifest.json`](../evals/reports/phase5_local_smoke/release_manifest.json) - authoritative merge-safe gate.
- [`evals/reports/native_regression/native_summary.json`](../evals/reports/native_regression/native_summary.json) - deterministic native regression summary.
- [`docs/benchmarks/README.md`](./benchmarks/README.md) - layered native and external benchmark docs.
- [`docs/benchmarks/PORTFOLIO.md`](./benchmarks/PORTFOLIO.md) - external benchmark portfolio boundaries.

## Interview Prep

- [`docs/VALUE_SCORECARD.md`](./VALUE_SCORECARD.md) - measured value pack: what is proven, what is not.

## Archived Code

- [`legacy/README.md`](../legacy/README.md) - archive root marker.
