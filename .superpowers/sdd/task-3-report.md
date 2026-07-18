# Task 3 Report: Durable Multi-Agent Research Runtime

Status: DONE

Commit: `907cc9c` (`feat: add durable multi-agent research runtime`)

## Scope Delivered

- Added a framework-independent, validated `ResearchDAG` and deterministic
  `ResearchPlanner`.
- Added an asyncio `ResearchScheduler` with dependency readiness, dynamic
  fan-out, configurable 1-8 worker concurrency, cooperative and externally
  polled cancellation, branch-local retries, monotonic events, and per-task
  checkpoints.
- Added provider-neutral worker protocols. Orchestration imports neither an
  OpenAI SDK nor PydanticAI. Model configuration snapshots pass through the
  Task 2 boundary, and tool calls use the governed Task 2 `ToolGateway`.
- Added scheduler-owned stable tool idempotency keys derived from the task
  contract, tool name, and canonical arguments. Retry-attempt keys supplied by
  a worker cannot duplicate a completed side effect.
- Added deterministic evidence reduction for exact record conflicts, evidence
  spans, semantic duplicate claims, content-identical document artifacts, and
  explicit unresolved semantic disagreements.
- Added deterministic evidence auditing with accepted, qualified,
  contradicted, and unsupported buckets. Optional semantic judgment can only
  downgrade the deterministic result.
- Added a V2 bundle compiler with frozen-manifest checks, exact evidence
  locators, graph-edge provenance validation, source hash degradation,
  deterministic canonical JSON, and structural executive-summary rebuilding
  from audited claim IDs only.
- Added a compatibility loader that validates V2 artifacts while returning old
  legacy JSON bundle shapes unchanged.
- Added `ResearchJobOrchestrator.run_dag(...)` as the scheduler bridge for new
  typed runs. The bridge freezes the supplied Task 2 snapshot in job metadata,
  persists task checkpoints, mirrors scheduler events, updates `scheduler-v2`
  job projections, and rechecks worker leases before any post-run write.
- Preserved the existing synchronous `run(...)` path for legacy checkpoints
  and legacy artifact reads.

## TDD Red Evidence

Initial focused collection failed before any Task 3 production modules existed:

```text
ERROR tests/test_multi_agent_runtime.py
ModuleNotFoundError: No module named 'deep_research_agent.orchestration'
ERROR tests/test_report_bundle_v2.py
ModuleNotFoundError: No module named 'deep_research_agent.auditor.semantic'
2 errors in 0.13s
```

The job bridge test then failed on the absent scheduler injection surface:

```text
TypeError: ResearchJobOrchestrator.__init__() got an unexpected keyword argument 'scheduler'
1 failed in 1.39s
```

The strengthened side-effect test changed worker idempotency keys on every
attempt and failed until the orchestration boundary derived a stable key:

```text
assert result.status == "completed"
E AssertionError: assert 'failed' == 'completed'
1 failed in 0.09s
```

Deterministic semantic claim merging and frozen graph provenance initially
failed together:

```text
assert ['claim-a', 'claim-b'] == ['claim-a']
Failed: DID NOT RAISE <class 'ValueError'>
2 failed in 0.11s
```

External cancellation polling and packet-artifact bundle consumption initially
failed together:

```text
TypeError: ResearchScheduler.__init__() got an unexpected keyword argument 'cancellation_poll_seconds'
assert [] == ['source-a']
2 failed in 0.17s
```

The scheduler bridge lease test reproduced a checkpoint write after a stolen
lease:

```text
assert not (... / 'scheduler_checkpoints.json').exists()
1 failed in 1.20s
```

The DAG initially accepted duplicate task idempotency keys:

```text
Failed: DID NOT RAISE <class 'ValueError'>
1 failed in 0.10s
```

The final audit hardening test proved an unsupported paraphrase could remain in
a caller-supplied executive summary before structural rebuilding:

```text
assert 'one hundred percent' not in executive_summary
1 failed in 0.08s
```

Each failure was observed before the corresponding production change, then
rerun individually to green.

## Green Evidence

Focused Task 3 suite after all implementation and review fixes:

```text
..............................                                           [100%]
30 passed in 1.28s
```

Existing job and auditor regressions:

```text
..................................                                       [100%]
34 passed in 1.92s
```

Task 1/2 boundaries plus the required runtime regression set:

```text
........................................................................ [ 38%]
........................................................................ [ 76%]
............................................                             [100%]
188 passed in 3.35s
```

Final full Python suite:

```text
........................................................................ [ 20%]
........................................................................ [ 41%]
........................................................................ [ 61%]
........................................................................ [ 82%]
...............................................................          [100%]
351 passed in 18.75s
```

Additional fresh completion gates:

- `uv run --no-config --default-index ... --locked ruff check .`:
  `All checks passed!`.
- `uv run --no-config --default-index ... --locked python main.py --help`:
  exit 0 and the canonical command surface rendered.
- `uv lock --no-config --default-index ... --check`: exit 0, 190 packages
  resolved, and `uv.lock` remained byte-for-byte unchanged.
- `git diff --check`: exit 0.
- Static provider-framework import scan of
  `src/deep_research_agent/orchestration`: exit 0 with no OpenAI,
  PydanticAI, or LangGraph imports.

## Self-Review And Concerns

- Scheduling decisions and event sequencing are owned by one coroutine. Worker
  completion order cannot race sequence allocation, and simultaneous
  completions are reduced in task-ID order.
- A failed task is retried without re-running completed siblings or ancestors.
  Descendants remain blocked until success and become explicit failed results
  when their dependency exhausts retries.
- Cancellation covers running and pending tasks. A token wakes the scheduler
  immediately; repository/service-backed cancellation checks are polled while
  workers are still running.
- Dynamic tasks are validated as a new immutable DAG revision. Unknown
  dependencies, cycles, conflicting task definitions, cross-job tasks, invalid
  output schemas, and duplicate idempotency keys fail closed.
- Tool results still use Task 2's timeout, tenant, budget, cache, and durable
  idempotency policies. The scheduler adds a stable operation key but does not
  bypass or duplicate gateway policy.
- Reduction handles structural duplicates only. It deliberately records
  differing support statuses for an explicit critic instead of guessing which
  semantic interpretation is correct.
- Critical claims with no valid frozen evidence are unsupported. Source hash
  mismatches degrade all claims using that document. Graph edges require known
  exact spans whose document versions are in the frozen manifest.
- Executive Summary sections are rebuilt from accepted and qualified audit
  buckets. Caller prose is not trusted for that section, so contradicted,
  unsupported, or paraphrased blocked claims cannot pass through it.
- The journal and worker interfaces are storage/provider neutral. Task 5
  production adapters must preserve append ordering and atomic checkpoint
  writes; the in-memory adapter is intentionally for tests and local execution.
- The existing synchronous orchestrator remains a compatibility path for old
  jobs. New typed runs enter through `run_dag(...)` and are labeled
  `scheduler-v2`; no legacy agent is imported by the orchestration package.
- No blocking concern remains for Task 3.

## Review Fixes (Task 3 Follow-up)

The review follow-up is implemented in a separate fix commit. The canonical
service now persists and dispatches an explicit `scheduler-v2` contract with a
frozen brief, DAG, and config snapshot; cancellation is wired into the
scheduler factory callback while the legacy runtime remains unchanged.

The scheduler globally deduplicates dynamic task declarations and rejects
conflicting definitions without retrying the declaring branch. Store mutations
for job projections, events, checkpoints, and scheduler sidecars are lease
fenced inside SQLite write transactions. Evidence claims and graph edges now
require supplied source artifacts with manifest-matching hashes. Typed critic
decisions are carried through worker output and run results, reduced, audited,
and reflected in bundle claim buckets; unresolved semantic disagreements cannot
become accepted critical claims. Executive-summary headings are canonicalized
case-insensitively with optional colons, duplicate headings fail closed, and a
canonical section is inserted when absent.

Follow-up verification:

```text
focused runtime + bundle regressions: 39 passed
full Python suite: 360 passed
ruff check src tests: All checks passed!
```

## Markdown Heading Completeness Fix

Final heading-normalization commit: `1f19d63`. The compiler now treats
repeated spaces, tabs, optional colons, ATX closing hashes, and Setext
`Executive Summary` forms as one canonical section. Duplicate detection runs
across mixed ATX/Setext forms, and caller summary prose is removed for every
recognized variant. Worker spawn commands also propagate explicit offline mode
or the configured production scheduler-factory path to the child process.

Focused red evidence initially showed three failures for whitespace/Setext
normalization and mixed duplicate detection. Green verification after the
fix:

```text
report-bundle regressions: 23 passed
runtime + bundle regressions: 49 passed
full Python suite: 370 passed
ruff check .: All checks passed!
```

Remaining operational concern: a production scheduler-v2 worker must inject a
provider-neutral `scheduler_factory`; the service intentionally fails closed
when a typed job is run without that factory instead of silently routing it to
the legacy orchestrator.

## Final Re-Review Fixes

The final re-review fixes are in follow-up commit `a6373e3` (after
`239b2a3` and `94e2bf5`). The summary sanitizer now recognizes ATX closing
hashes such as `## Executive Summary ##`. Heartbeats use a lease-conditional
SQLite update, so an old worker cannot refresh a replacement or terminal job.
The worker composition root now selects an explicitly configured production
factory and offers a deterministic scheduler only for explicit offline mode;
legacy jobs remain on the legacy path without requiring a scheduler factory.

Critic rationale spans are validated against both reduced spans and supplied
source artifacts whose content hashes match the frozen corpus manifest. Multiple
distinct valid critic decisions covering one claim are treated as unresolved
instead of last-write-wins.

Focused red evidence before these changes included four failures for the
closing-hash, heartbeat/composition, rationale-source, and overlap cases. The
green verification after `a6373e3` was:

```text
focused runtime + bundle regressions: 45 passed
full Python suite: 366 passed
ruff check src tests: All checks passed!
```
