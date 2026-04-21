# Phase 3 — Connectors, evidence, audit, reporting

## Objective
Implement the evidence-first research pipeline from source acquisition to report bundle.

## Required outcomes
- search / fetch / file-ingest abstraction
- at least these first-class connectors:
  - web
  - github
  - arxiv
  - files
- source policy integration
- snapshot storage
- document normalization/chunking
- evidence fragments
- claim objects
- support/conflict edges
- audit gate
- review queue if blocked
- report bundle rendering

## Must produce
- one end-to-end research flow
- artifacts that let a reader trace:
  `claim -> evidence -> snapshot/source`
- concrete output files such as:
  - report.md
  - report_bundle.json
  - claims.json
  - sources.json
  - audit_decision.json
  - trace.jsonl
  - manifest.json

## Constraints
- report prose is not the source of truth
- bundle JSON is the source of truth
- unsupported claims must not appear as confident findings

## Acceptance
This phase passes only when:
- one full research job can run end to end
- the emitted artifacts are real and inspectable
- claim/evidence/snapshot traceability exists
- blocked or low-support situations are surfaced through audit artifacts
- focused integration tests pass

## Validation
Run at least:
- integration tests for connectors/policy/snapshot
- integration tests for claim/audit/reporting path
- one real or frozen-snapshot research job smoke
- artifact schema validation