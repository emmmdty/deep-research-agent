# LongFact / SAFE

## Current role

- role: `external_regression`
- current implementation: committed smoke fixture with official-style `precision`, `recall`, and `f1_at_k`
- not a merge-blocking release gate

## Current entrypoints

- `python scripts/run_longfact_safe.py --subset smoke --output-root <dir> --json`
- `python main.py benchmark run --benchmark longfact_safe --subset smoke --output-root <dir> --json`

## Backend logging

- `internal_diagnostics.json` records:
  - `search_backend`
  - `judge_backend`
  - `latency_cost`
  - `drift_risk`

## Cost and drift caveats

- SAFE-style evaluation can drift when live search or live judge models change.
- This repo keeps the smoke path deterministic and local until a live backend is explicitly configured.
- If a future environment lacks the required backend, the harness should emit a blocked report instead of inventing scores.
