# GUI Benchmark Console

The Phase 23 benchmark console exposes the repository's existing native benchmark evidence in the web GUI. It is a reviewer surface, not a new benchmark orchestrator.

## Evidence Sources

- Authoritative merge gate: `evals/reports/phase5_local_smoke/release_manifest.json`
- Regression layer: `evals/reports/native_regression/release_manifest.json`
- Native summary: `evals/reports/native_regression/native_summary.json`
- Scorecard: `docs/benchmarks/native/NATIVE_SCORECARD.md`
- Casebook: `docs/benchmarks/native/CASEBOOK.md`

## Displayed Suites

| Suite | smoke_local tasks | regression_local tasks | Status |
| --- | ---: | ---: | --- |
| `company12` | 1 | 12 | passed |
| `industry12` | 1 | 12 | passed |
| `trusted8` | 1 | 8 | passed |
| `file8` | 1 | 8 | passed |
| `recovery6` | 6 | 6 | passed |

## GUI Boundaries

- The console presents committed deterministic local artifacts.
- It does not add external benchmark integrations.
- It does not start long-running benchmark jobs from the browser.
- The release gate remains `smoke_local`; `regression_local` is reviewer-facing wider coverage.

## Local Verification

```bash
cd apps/gui-web
npm test
npm run lint
npm run build
```

Backend boundary smoke remains:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts
```
