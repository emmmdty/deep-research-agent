# API Readiness Contract

Status: draft

当前没有受支持的 HTTP/API server surface。本文是目标契约，不是当前实现。

本文只说明未来 server/API 应复用哪些边界，以及实现前必须先解决哪些生产化前置条件。

## Current Public Surface

当前公开入口：

- `main.py submit`
- `main.py status`
- `main.py watch`
- `main.py cancel`
- `main.py retry`

当前公开 runtime：

- `services/research_jobs/`
- `connectors/`
- `policies/`
- `auditor/`
- report bundle / trace / snapshot / audit sidecar artifacts

当前不公开：

- HTTP/API server
- web UI
- multi-tenant job API
- external queue / worker pool
- legacy graph as API boundary

## Target Resource Contract

以下是目标契约，不是当前实现。

### Jobs

- create job
- read job
- watch job events
- request cancel
- create retry from prior job

目标语义必须保留：

- deterministic job lifecycle
- worker lease ownership
- append-only event log
- monotonic checkpoint sequence
- stale recovery without active lease overwrite

### Artifacts

- read report bundle
- read report text
- read trace events
- read source snapshot manifest
- read audit sidecars

目标语义必须避免：

- exposing local filesystem paths as stable external IDs
- returning report prose without structured claim/evidence links
- hiding blocked audit gate status

### Sources

- submit source profile
- inspect policy decisions
- inspect connector health
- inspect snapshot metadata

目标语义必须保留：

- connector -> policy -> snapshot path
- fetch security rejection reasons
- `snapshot_ref` provenance

### Audit

- read claim graph
- read claim support edges
- read critical claim review queue
- read conflict sets
- read audit gate summary

目标语义必须保留：

- critical claim without grounded evidence remains blocked
- `passed` does not mean complete automatic fact verification
- review queue is visible when blocked

## Required ADRs Before Implementation

Server implementation must not start before these topics are decided:

- auth and tenant boundary
- production storage boundary
- queue and worker orchestration
- artifact object storage and retention
- rate limit and budget enforcement
- audit log retention
- migration compatibility for existing workspace artifacts

## Compatibility Notes

- Existing CLI stays supported during the next release train.
- `legacy-run` remains hidden and compatibility-only.
- benchmark/comparator outputs remain diagnostics and do not define API readiness.
- release gate must remain blocked if API docs claim current HTTP/API support before implementation is accepted.
