# GAIA

## Current role

- role: `challenge_track`
- scope: supported subset only
- unsupported capabilities should be filtered or blocked, not counted as benchmark failures

## Entrypoints

- `python scripts/run_gaia_subset.py --subset smoke_supported --output-root <dir> --json`
- `python main.py benchmark run --benchmark gaia --subset smoke_supported --output-root <dir> --json`

## Supported capability policy

- current supported capabilities:
  - `text`
  - `file_read`
- current smoke fixture sanitizes attachment paths before writing result metadata
