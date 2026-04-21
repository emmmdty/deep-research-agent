# ADR-0008: Expose a local HTTP API over the deterministic job runtime

- Status: Accepted
- Date: 2026-04-21

## Context

By the end of Phase 3, the repository already had the required internal building blocks:

- deterministic job lifecycle
- append-only events and checkpoints
- stable bundle and audit artifacts
- explicit source-profile and audit-gate contracts

Phase 4 needed a real HTTP API, but without pretending the local SQLite/filesystem runtime was already a production multi-tenant control plane.

## Decision

- Implement a local FastAPI surface that wraps `ResearchJobService`.
- Keep the HTTP API job-oriented:
  - submit
  - get status
  - stream events by polling
  - cancel
  - retry
  - resume
  - refine
  - review
  - read bundle
  - read named artifacts
- Return stable API URLs for artifacts instead of leaking local filesystem paths in the public response contract.
- Keep the underlying runtime unchanged: SQLite, filesystem artifacts, and local subprocess worker remain the actual execution substrate in Phase 4.
- Export a module-level `app` so local serving is reproducible with `uvicorn deep_research_agent.gateway.api:app`.

## Consequences

- The CLI and HTTP API now share the same lifecycle semantics and the same underlying job store.
- Public docs can describe a real API instead of a readiness-only placeholder.
- Future server-grade storage and queue migrations can preserve the route contract while swapping the internals.

## Rejected Alternatives

### Expose raw `JobRuntimeRecord` directly

Rejected because it would bake local file paths and worker-internal fields into the public API contract.

### Wrap the legacy LangGraph runtime as the server boundary

Rejected because the repository’s supported control plane is the deterministic research job runtime, not the archived multi-agent graph.
