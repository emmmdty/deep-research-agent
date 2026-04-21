# Phase 5 — Tests, evals, release gates

## Objective
Turn the rebuilt system into an evaluable and releasable engineering artifact.

## Required outcomes
- lint/unit/integration/e2e coverage
- reliability tests for cancel/retry/resume/stale recovery
- provider fallback or switching checks
- source policy restriction checks
- file-ingest and long-document checks
- company/industry research eval tasks
- release gate runner/checklist
- experiment artifacts and summaries

## Must produce
- test suite organization matching the new architecture
- eval runners and configs
- at least low-cost/smoke results locally
- heavy eval harnesses and commands prepared if the current machine cannot run all heavy workloads
- results manifests and summaries in docs or experiments outputs

## Constraints
- do not rely only on old benchmark scripts
- do not declare success without artifacts
- if a heavy experiment cannot run here, implement the harness and run the low-cost version

## Acceptance
This phase passes only when:
- relevant tests pass
- at least one company-research and one industry-research task emit report bundles
- reliability scenarios are exercised
- release gate checklist exists and is runnable
- results/manifests are stored

## Validation
Run at least:
- lint
- unit tests
- integration tests
- e2e smoke
- one reliability suite
- one source-policy suite
- one file-ingest suite
- one or more eval tasks with saved outputs