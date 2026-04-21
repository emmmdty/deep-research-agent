# Experiment Summary

## Scope

The authoritative local experiment pack is the Phase 5 deterministic smoke set
checked into `evals/reports/phase5_local_smoke/`.

It covers:

- `company12`
- `industry12`
- `trusted8`
- `file8`
- `recovery6`

The release decision is recorded in:

- `evals/reports/phase5_local_smoke/release_manifest.json`

## Current Result Snapshot

From the committed `release_manifest.json`:

- release gate: `passed`
- `company12`: `passed` with `completion_rate=1.0`, `audit_pass_rate=1.0`, `policy_compliance_rate=1.0`
- `industry12`: `passed` with `completion_rate=1.0`, `audit_pass_rate=1.0`, `policy_compliance_rate=1.0`
- `trusted8`: `passed` with `completion_rate=1.0`, `audit_pass_rate=1.0`, `policy_compliance_rate=1.0`
- `file8`: `passed` with `completion_rate=1.0`, `audit_pass_rate=1.0`, `policy_compliance_rate=1.0`
- `recovery6`: `passed` with `completion_rate=1.0`, `resume_success_rate=1.0`, `stale_recovery_success_rate=1.0`

## Verification Commands

```bash
uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json
uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json
uv run python main.py eval run --suite trusted8 --output-root evals/reports/phase5_local_smoke/trusted8 --json
uv run python main.py eval run --suite file8 --output-root evals/reports/phase5_local_smoke/file8 --json
uv run python main.py eval run --suite recovery6 --output-root evals/reports/phase5_local_smoke/recovery6 --json
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
```

## Determinism Notes

- Saved smoke outputs are normalized so rerunning the same command on the same path is byte-stable.
- File-ingest fixtures are serialized with repo-relative paths and `repo:///...` URIs, so the committed artifacts do not depend on a specific checkout location.
- The final Phase 5 `main` rerun left `git status --short` clean after executing the release smoke against the committed output path.

## Remaining Limits

- These are low-cost local smoke suites, not the full heavy benchmark/comparator portfolio.
- The heavy benchmark/comparator tooling remains available for diagnostics, but it is not the release gate.
- The current release contract is intentionally local and deterministic.
