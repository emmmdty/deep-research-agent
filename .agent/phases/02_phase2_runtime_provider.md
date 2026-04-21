# Phase 2 — Runtime and provider layer

## Objective
Implement the deterministic runtime core and the provider abstraction before finishing the broader research pipeline.

## Required outcomes
- canonical job model
- canonical event/checkpoint model
- deterministic state transitions
- explicit separation of `status` and `audit_gate_status`
- provider abstraction layer for:
  - OpenAI
  - Anthropic
  - openai-compatible
  - anthropic-compatible
- config/schema/profile foundations
- local profile smoke path

## Must produce
- runtime service code
- provider router code
- provider capability/config models
- test coverage for state transitions and provider config loading
- updated docs if the public invocation path changed

## Constraints
- no fake provider abstraction
- do not hard-code business logic to one SDK
- do not postpone state model cleanup

## Acceptance
This phase passes only when:
- a local smoke path can create and drive a research job lifecycle
- provider configs load for all required provider classes
- manual and automatic provider routing exist
- `status` and `audit_gate_status` are separate in code and tests
- relevant runtime/provider tests pass

## Validation
Run at least:
- runtime unit tests
- provider/config unit tests
- one CLI smoke for create/status/cancel/retry/resume or equivalent
- lint/typecheck on the new modules