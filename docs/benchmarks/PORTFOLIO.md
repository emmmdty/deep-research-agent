# Benchmark Portfolio

## Purpose

The external benchmark portfolio complements the Deep Research Agent's native release gate. It does not replace it.

The authoritative release decision still comes from the deterministic Phase 5 local smoke pack under `evals/reports/phase5_local_smoke/`.

## Current layers

| Layer | Current items | Current status | Release meaning |
| --- | --- | --- | --- |
| authoritative release gate | native Phase 5 local smoke suites (`company12`, `industry12`, `trusted8`, `file8`, `recovery6`) | implemented and committed | merge-blocking source of truth |
| secondary regression | FACTS Grounding open smoke | implemented | required for RC-style benchmark reporting, not a merge gate |
| external regression | LongFact / SAFE smoke; LongBench v2 short smoke | implemented | useful regression signal, not the release decision |
| challenge track | BrowseComp guarded smoke; GAIA supported subset; LongBench v2 medium/long challenge policy | guarded/subset-first; medium currently blocked; long remains deferred | informative only |
| deferred | private/blind submissions, GAIA multimodal coverage, official leaderboard submissions, fully measured live provider-routing deltas | not implemented | future work |

## Current implemented adapters

| Benchmark | Adapter mode | Current scope | Entrypoints |
| --- | --- | --- | --- |
| FACTS Grounding | `facts_doc_grounded_longform` | `split=open`, `subset=smoke` | `main.py benchmark run --benchmark facts_grounding ...`, `scripts/run_facts_grounding.py` |
| LongFact / SAFE | `longfact_safe_open_domain_longform` | `subset=smoke` | `main.py benchmark run --benchmark longfact_safe ...`, `scripts/run_longfact_safe.py` |
| LongBench v2 | `longbench_mcq_longcontext` | `bucket=short`, `subset=smoke`; `bucket=medium` blocked harness | `main.py benchmark run --benchmark longbench_v2 ...`, `scripts/run_longbench_v2.py` |
| BrowseComp | `browsecomp_short_answer` | guarded `subset=smoke` | `main.py benchmark run --benchmark browsecomp ...`, `scripts/run_browsecomp_guarded.py` |
| GAIA | `gaia_capability_gated` | supported `subset=smoke_supported` | `main.py benchmark run --benchmark gaia ...`, `scripts/run_gaia_subset.py` |

## Summary artifact

The reviewer-facing rollup lives at:

- `evals/external/reports/portfolio_summary/portfolio_summary.json`
- `evals/external/reports/portfolio_summary/README.md`

Generate or refresh it with:

```bash
uv run python scripts/build_benchmark_portfolio_summary.py --output-root evals/external/reports/portfolio_summary --json
```

The summary builder overlays any discovered `benchmark_run_manifest.json` files onto the static adapter catalog. That means:

- implemented smoke fixtures still appear even before a fresh run
- blocked challenge runs are recorded as blocked, not fabricated into scores
- the native release gate keeps its own authority and separate artifact path

## Interpretation rules

- FACTS Grounding is the first external regression layer because it is closest to the repo's claim/evidence/audit contract.
- LongFact / SAFE and LongBench short are external regression diagnostics, not the release gate.
- BrowseComp and GAIA stay challenge-only even when their guarded/supported smoke runs pass.
- LongBench v2 medium and long must remain capability-sensitive. Blocked is an acceptable result when the required long-context backend is unavailable.
- Legacy heavy benchmark/comparator tooling remains diagnostic only and should not be confused with this external benchmark substrate.
