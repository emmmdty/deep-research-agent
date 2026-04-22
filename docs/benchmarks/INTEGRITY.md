# Benchmark Integrity

## Purpose

This portfolio keeps benchmark-specific integrity findings separate from the native release gate.

Reviewer rollups live in:

- `evals/external/reports/portfolio_summary/portfolio_summary.json`
- `evals/external/reports/portfolio_summary/README.md`
- `docs/benchmarks/PORTFOLIO.md`

## Current guards

- BrowseComp: denylist, canary detection, query redaction, integrity manifest
- GAIA: capability filtering, attachment path sanitization
- LongBench v2: bucket assignment and truncation diagnostics
- LongFact / SAFE: search/judge backend logging

## Current rule

- challenge tracks are informative, not merge-blocking
- unsupported or unavailable capabilities must emit blocked reports, not fabricated scores
- the portfolio summary must report blocked challenge runs as blocked instead of silently dropping them
- the native Phase 5 local smoke pack remains the only authoritative release gate
