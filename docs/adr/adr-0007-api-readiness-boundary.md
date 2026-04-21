# ADR-0007: API readiness boundary before implementation

- Status: Superseded by ADR-0008
- Date: 2026-04-20

## Historical Context

Before Phase 4, the repository intentionally documented a CLI-first boundary and rejected premature server work. That decision was correct for the pre-API state because the runtime, bundle, and audit contracts were still stabilizing.

## Historical Decision

- The public entrypoint remained `main.py submit/status/watch/cancel/retry`.
- No server entrypoint or listener port was exposed before the deterministic runtime and artifact boundaries were stable.
- Future API work had to wrap the job-oriented runtime, not the legacy graph.

## Why It Is Superseded

Phase 4 implemented the local HTTP API after the runtime, connector, auditor, and bundle contracts were already merged to `main`.

The current decision is captured in:

- [ADR-0008](./adr-0008-http-api-surface.md)
- [ADR-0009](./adr-0009-batch-and-artifact-contract.md)
- [`specs/api-readiness-contract.md`](../../specs/api-readiness-contract.md)

## Consequence

This ADR remains as historical context only. It should not be read as the current public-surface truth.
