# Phase 18 — Chinese usage manual and handoff

## Objective
Create a simplified Chinese usage manual and finalize the optimization-cycle handoff.

## Required outputs
Create:
- `docs/benchmarks/native/USAGE_GUIDE.zh-CN.md`
- `docs/final/NATIVE_OPTIMIZATION_REPORT.md`

Update as needed:
- `README.md`
- `docs/benchmarks/native/README.md`
- `docs/final/EXPERIMENT_SUMMARY.md`

## Manual requirements
The Chinese manual must explain:
- what smoke_local is
- what regression_local is
- why smoke_local remains the release gate
- how to rerun smoke_local and regression_local
- how to inspect report cases and bundles
- how to read release_manifest.json and native_summary.json
- how to interpret the key metrics
- what the latest optimization cycle changed
- what is still not covered

## Acceptance
This phase passes only when:
- the Chinese manual exists and is readable by a reviewer who did not build the repo
- the final report exists and summarizes the optimization cycle
- README/native benchmark docs point to the new manual
- final mainline validation passes and `git status --short` is clean

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused benchmark tests
- one smoke_local command
- one affected regression_local command
- `git status --short`
