# BrowseComp

## Current role

- role: `challenge_track`
- scope: guarded smoke only
- explicitly not part of the authoritative release gate

## Integrity guards

- `benchmark_material_denylist`
- `canary_string_detection`
- `query_redaction`
- `integrity_findings_manifest`

## Entrypoints

- `python scripts/run_browsecomp_guarded.py --subset smoke --output-root <dir> --json`
- `python main.py benchmark run --benchmark browsecomp --subset smoke --output-root <dir> --json`
