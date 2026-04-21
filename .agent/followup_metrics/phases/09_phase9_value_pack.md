# Phase 9 — Value-pack and signoff

## Objective
Convert the measured outputs into a public, interview-ready, reviewer-friendly value pack.

This phase must make the project’s impact legible.

## Required outcomes
Create:
- `docs/final/VALUE_SCORECARD.md`
- `docs/final/VALUE_SCORECARD.json`

Update:
- `README.md`
- `docs/final/EXPERIMENT_SUMMARY.md`
- `FINAL_CHANGE_REPORT.md`

## Required content of VALUE_SCORECARD.md
It must include:

1. Current repository baseline
2. What the Deep Research Agent does
3. Why this is not a chat shell or toy demo
4. Headline metrics table
5. Ablation summary table
6. Reliability summary
7. Source-policy and audit summary
8. File-ingest and cross-source summary
9. Latency/cost summary
10. Clear interpretation:
   - what improved versus weaker baselines
   - what remains local-only
   - what is still not production-grade SaaS

## README updates
Add a concise section near the top that includes:
- one-sentence positioning
- 5–8 headline metrics
- links to:
  - `docs/final/VALUE_SCORECARD.md`
  - `docs/final/EXPERIMENT_SUMMARY.md`
  - `evals/reports/phase5_local_smoke/release_manifest.json`

## Required public-facing metric language
The final docs must make these claims measurable:

- “This agent does not just generate prose; it emits grounded report bundles.”
- “This agent does not just search; it preserves source policy and provenance.”
- “This agent is not a single-shot script; it survives cancel/retry/resume/stale-recovery flows.”
- “This architecture is better than weaker baselines on the metrics that matter.”

## Constraints
- do not hide limitations
- explicitly preserve the current limit that the HTTP API is local-only
- do not market the current repo as a multi-tenant production SaaS
- do not use raw word count, citation count, or report length as proof of value

## Acceptance
This phase passes only when:
- `VALUE_SCORECARD.md` and `.json` exist
- README headline metrics are updated
- the final docs cite real artifact paths and real measured values
- the final mainline smoke passes
- `git status --short` is clean after the final rerun

## Validation
Run at least:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- the broad regression slice from the existing command registry
- one CLI smoke
- one API smoke
- one scorecard generation command or final doc verification command
- `git status --short`

## Final stop rule
This is the last phase.
At the end:
- merge into `main`
- rerun final smoke on `main`
- remove the last worktree
- delete the last branch
- write the final follow-up status summary