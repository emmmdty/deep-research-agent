# Phase 4 — API, CLI, batch, docs

## Objective
Expose the system through stable public surfaces and make the repository reproducible by documentation.

## Required outcomes
- HTTP API for async jobs
- stable CLI for developer use
- batch execution path
- updated README
- updated architecture/development/evaluation docs
- ADRs for the most important architectural decisions
- migration doc describing what was archived/deleted and why

## Must produce
- API routes and schemas
- CLI commands
- docs that match the real code
- at least one documented reproduction/demo flow

## Constraints
- do not build a frontend
- docs must reflect actual code, not idealized design
- API contract must match runtime behavior

## Acceptance
This phase passes only when:
- async job submit/status/result retrieval works via the HTTP API
- CLI path is usable
- batch path exists
- docs are updated and coherent
- basic API/CLI smoke tests pass

## Validation
Run at least:
- API smoke tests
- CLI smoke tests
- doc command checks where practical
- schema validation for public request/response contracts
