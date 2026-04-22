# FACTS Grounding

## Current role

- role: `secondary_regression`
- scope in this repo today: committed open smoke fixture plus shared adapter/manifest wiring
- not a replacement for the native authoritative release gate

## Phase 10 implementation

- public entrypoints:
  - `python main.py benchmark run --benchmark facts_grounding --split open --subset smoke --output-root <dir> --json`
  - `python scripts/run_facts_grounding.py --split open --subset smoke --output-root <dir> --json`
- artifact contract:
  - `benchmark_run_manifest.json`
  - `official_scores.json`
  - `internal_diagnostics.json`
  - `task_results.jsonl`
  - `integrity_report.json`
  - `README.md`

## Current limits

- The committed smoke path uses a local open fixture to validate adapter, manifest, and score plumbing.
- It is suitable for regression wiring and repo-local smoke only.
- Private/blind FACTS execution is deferred; no private submission automation is implemented in Phase 10.

## Metrics

- official-style:
  - `eligibility_score`
  - `grounding_score`
- internal:
  - `critical_claim_support_precision`
  - `citation_error_rate`
  - `provenance_completeness`
