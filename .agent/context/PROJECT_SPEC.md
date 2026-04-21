# Project Spec

## Product positioning
Build an enterprise Deep Research Agent for company/industry research.

## Core outcome
Transform the current repository into a system with:
- deterministic job runtime
- evidence-first research pipeline
- claim-level audit
- source policy and snapshotting
- report bundle artifacts
- OpenAI + Anthropic provider abstraction
- CLI + HTTP API + batch entrypoints
- evaluation suites and release gates

## Non-goals
- No chat frontend
- No toy demo positioning
- No multi-agent-count storytelling
- No preserving old internal compatibility just for safety
- No event-extraction platform pivot
- No dependence on a single closed provider for the system’s core value

## Required architecture principles
- deterministic runtime owns lifecycle
- LLM-assisted steps operate inside bounded stages
- evidence objects precede prose
- `status` and `audit_gate_status` are separate contracts
- every evidence must resolve to a snapshot
- source policy is mandatory
- bundle JSON is the authoritative output
- evals and release gates define readiness
- local dev profile and server profile are both first-class

## Required public surfaces
- developer-friendly CLI
- HTTP API for async jobs
- batch execution path
- report bundle artifacts
- no fancy frontend

## Required providers
- OpenAI
- Anthropic
- openai-compatible base_url
- anthropic-compatible base_url
- manual and automatic routing

## Resource profile
Local machine:
- CPU-only development
- unit tests
- lightweight integration
- smoke evals

Server:
- 1-2 x 4090
- heavy evals
- reranker / embedding experiments
- long jobs
- batch processing

## Must-keep assets
- valuable tests
- useful connector logic
- job orchestration primitives
- snapshot/source policy assets
- claim audit primitives
- benchmark fixtures with migration value

## Must-archive or delete
- old multi-agent graph as product truth
- report-shape metrics as release authority
- toy memory abstractions
- placeholder MCP content
- legacy workflow code on the main execution path

## Definition of done
The project is done when:
- the new architecture boundary is explicit in code and docs
- the main research path runs end to end
- providers are abstracted cleanly
- jobs are async, cancellable, resumable, retryable
- evidence-first report bundles are emitted
- key tests and eval suites pass
- release gates are implemented
- docs can drive a fresh reproduction