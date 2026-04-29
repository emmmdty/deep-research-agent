# Phase 4 Surface Migration

## Purpose

This note records the public-surface migration performed in Phase 4.

## What Changed

- The repository no longer documents the HTTP API as a readiness-only future contract.
- A local FastAPI surface now exists at `deep_research_agent.gateway.api`.
- The CLI now includes:
  - `bundle`
  - `batch run`
- The public API uses stable artifact URLs and stable artifact names instead of exposing workspace paths as its contract.

## Archived Or Superseded Items

- `docs/adr/adr-0007-api-readiness-boundary.md` is now historical context only and was superseded by ADR-0008.
- `specs/api-readiness-contract.md` keeps its path for link stability, but its content now describes the implemented Phase 4 API instead of a pre-implementation readiness placeholder.
- The old regression `tests/test_phase6_api_readiness.py` was removed because it asserted the absence of an HTTP API, which is no longer the target-state truth.

## Items Kept Intentionally

- `legacy-run` remains hidden and compatibility-only.
- The underlying local runtime is still SQLite + filesystem + local subprocess worker.
- The report bundle remains the authoritative machine-readable output.

## Follow-On Work Deferred To Later Phases

- auth and tenant boundary
- external queue / worker pool
- object storage indirection
- stronger review-to-bundle synchronization
- release-gated API and batch evaluation suites
