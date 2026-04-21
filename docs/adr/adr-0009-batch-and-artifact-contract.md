# ADR-0009: Keep batch and artifact delivery on the same public contract

- Status: Accepted
- Date: 2026-04-21

## Context

Phase 4 required both a batch path and a reproducible artifact surface. The repository already produced named bundle sidecars, but the public surfaces still needed a stable way to:

- submit many jobs with one contract
- fetch artifacts without binding callers to workspace paths
- keep CLI and API semantics aligned

## Decision

- Batch submission reuses the same per-job request contract as single-job submission.
- The HTTP batch endpoint accepts `{"jobs": [...]}` and returns the accepted jobs immediately.
- The CLI batch surface reads JSON or JSONL files and submits each entry through `ResearchJobService.submit()`.
- Artifact access is keyed by stable names such as `report_bundle.json`, `manifest.json`, `review_queue.json`, and `claim_graph.json`.
- The HTTP API maps those stable names to the current local file layout, so callers do not depend on workspace-relative paths.
- The CLI keeps its developer-oriented JSON output style; the HTTP API owns the stricter public response projection.

## Consequences

- Batch runs and single-job runs stay contract-compatible.
- Docs can publish one artifact-name list instead of filesystem-specific examples.
- Future object-storage or artifact-service work can preserve artifact names even if file locations change.

## Rejected Alternatives

### Give batch its own custom job schema

Rejected because it would create two creation contracts for the same runtime and increase drift between CLI and API.

### Expose artifact paths directly in API responses

Rejected because local paths are implementation details and would become a brittle public dependency.
