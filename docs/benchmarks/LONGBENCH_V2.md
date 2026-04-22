# LongBench v2

## Current role

- role: `external_regression` for `short`
- role: `challenge_track` for `medium` / `long`

## Current entrypoints

- `python scripts/run_longbench_v2.py --bucket short --subset smoke --output-root <dir> --json`
- `python main.py benchmark run --benchmark longbench_v2 --bucket short --subset smoke --output-root <dir> --json`

## Current implementation

- `short` bucket: committed local MCQ smoke fixture with official-style accuracy outputs
- `medium` bucket: blocked harness until a long-context backend is explicitly enabled

## Diagnostics

- official-style:
  - `accuracy_overall`
  - `accuracy_by_bucket`
  - `accuracy_by_category`
- internal:
  - `truncation_rate`
  - `stage_runtime_seconds`

## Limits

- This phase does not force LongBench v2 through the report-bundle output shape.
- The `medium` and `long` paths are capability-sensitive and should emit blocked reports rather than fabricated scores when long-context capacity is unavailable.
