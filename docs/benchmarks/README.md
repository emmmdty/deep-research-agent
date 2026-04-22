# Benchmark Docs

This directory documents the layered benchmark portfolio that now sits next to the native Phase 5 release gate.

## Reviewer entrypoints

- [Portfolio overview](./PORTFOLIO.md)
- [Portfolio summary README](../../evals/external/reports/portfolio_summary/README.md)
- [Portfolio summary JSON](../../evals/external/reports/portfolio_summary/portfolio_summary.json)

## Engineer entrypoints

- [FACTS Grounding](./FACTS_GROUNDING.md)
- [LongFact / SAFE](./LONGFACT_SAFE.md)
- [LongBench v2](./LONGBENCH_V2.md)
- [BrowseComp](./BROWSECOMP.md)
- [GAIA](./GAIA.md)
- [Integrity rules](./INTEGRITY.md)

## Current layering

- authoritative release gate: native Phase 5 local smoke suites under `evals/reports/phase5_local_smoke/`
- secondary regression: FACTS Grounding open smoke
- external regression: LongFact / SAFE smoke and LongBench v2 short smoke
- challenge track: BrowseComp guarded smoke, GAIA supported subset, and LongBench v2 medium/long challenge policy
- deferred: private/blind submissions, GAIA multimodal coverage, and fully measured live provider-routing deltas
