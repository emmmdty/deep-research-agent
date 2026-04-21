# Phase 1 — Structure rebuild

## Objective
Establish the target repository shape so the new system can be implemented cleanly.

## Required outcomes
- create `src/deep_research_agent/` as the canonical package root
- create top-level boundaries for:
  - gateway
  - research_jobs
  - connectors
  - policy
  - evidence_store
  - auditor
  - reporting
  - providers
  - retrieval
  - storage
  - observability
- move or archive legacy code
- simplify `main.py` into a thin wrapper
- update packaging/imports/entrypoints accordingly

## Migration intent
- keep valuable modules by moving them
- archive old graph/agent narrative
- do not preserve old internal layout for compatibility

## Must produce
- clear directory tree
- archive location for legacy code
- import path updates
- updated README snippets if entrypoints changed
- migration notes for major moves/deletions

## Acceptance
This phase passes only when:
- the new package tree exists
- legacy code no longer sits on the main execution path
- packaging/imports resolve
- a basic import smoke passes
- the repo is structurally closer to the target blueprint than the old layout

## Validation
Run at least:
- import/compile smoke
- lint or syntax check for touched files
- the best available focused tests after the move
- one CLI entrypoint smoke if still available

Record moved/archived/deleted paths explicitly.