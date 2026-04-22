Treat AGENTS.md as the base control layer.

This run is a native-benchmark preflight only.
Do NOT start benchmark implementation.
Do NOT create worktrees.
Do NOT start external benchmark integration.
Do NOT touch BrowseComp, GAIA, FACTS Grounding, LongFact/SAFE, or LongBench v2 in this run.

Scope of this preflight:
Only audit readiness for the repository’s native/custom benchmark track:
- company12
- industry12
- trusted8
- file8
- recovery6

Goal:
Determine whether the current repository and local environment are ready for:
1. rerunning the current smoke_local native benchmark pack
2. expanding native benchmark from smoke to regression tier
3. running provider-backed full native benchmark tasks with real research jobs

Read these files in order before doing anything else:
1. AGENTS.md
2. .agent/context/PROJECT_SPEC.md
3. .agent/context/TASK2_SPEC.yaml
4. .agent/STATUS.md
5. README.md
6. FINAL_CHANGE_REPORT.md
7. docs/final/EXPERIMENT_SUMMARY.md
8. evals/reports/phase5_local_smoke/release_manifest.json

Then inspect the live repository.

This is a preflight audit only.
You may create or update only preflight documentation under `.agent/native_benchmark/`.
Do not modify application code in this run unless a broken file reference in documentation makes the preflight itself impossible.

Create or update these files:
- `.agent/native_benchmark/PREFLIGHT_NATIVE_BENCHMARK_AUDIT.md`
- `.agent/native_benchmark/STATUS.md`

What to audit:

A. Current native benchmark truth
- confirm which native suites exist
- confirm each suite’s current variant/tier (smoke_local, regression, full, unknown)
- confirm task counts from the committed manifest
- confirm which current commands are the canonical native benchmark entrypoints
- confirm which current metrics and thresholds are already available for native benchmark runs

B. Repo readiness for native benchmark expansion
- inspect evals/, scripts/, tests/, src/deep_research_agent/evals/, configs/release_gate.yaml, and related docs
- determine:
  - what can already be reused
  - what native-only benchmark harness pieces are missing
  - what data/task/rubric gaps prevent moving beyond smoke
  - whether current output artifacts are enough for benchmark-level reporting

C. Local configuration and assets
Check explicitly:
- `.env`
- provider-related env vars if present
- local Python / uv environment usability
- source-profile files
- eval fixture/data roots
- output-root writability using `/tmp/native_benchmark_preflight/...`
- local file-ingest fixture availability
- workspace/runtime directories if needed for native eval execution

Important:
- `.codex/config.toml` is optional in this run and must NOT be treated as a blocker.
- Only mark a config as required if the current native benchmark or the proposed provider-backed full native benchmark truly depends on it.

D. Tiered readiness
You must determine the highest native-benchmark tier currently supported:

Tier 1: `READY_FOR_CURRENT_SMOKE`
Meaning:
- the current smoke_local pack can be rerun cleanly now

Tier 2: `READY_FOR_NATIVE_REGRESSION_EXPANSION`
Meaning:
- the repo is ready to start implementing a larger native regression pack
- no critical config/access blocker prevents that implementation work
- current code/docs are sufficient to begin expanding task counts, rubrics, and reporting

Tier 3: `READY_FOR_PROVIDER_BACKED_FULL_NATIVE_RUN`
Meaning:
- provider-backed full native benchmark runs with real research jobs are configuration-ready now
- required provider/config access is present
- local environment is ready to execute at least a smoke version of such runs

Tier 0: `NOT_READY`
Meaning:
- a real blocker exists even before implementation can safely begin

You must return exactly one readiness verdict from:
- READY_FOR_CURRENT_SMOKE
- READY_FOR_NATIVE_REGRESSION_EXPANSION
- READY_FOR_PROVIDER_BACKED_FULL_NATIVE_RUN
- NOT_READY

E. Required validation actions
Run only safe preflight checks.
At minimum:
1. parse/read the current repo and benchmark docs
2. inspect the current native manifest and suite inventory
3. run:
   - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help`
4. run one direct native suite smoke into /tmp, for example:
   - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite company12 --output-root /tmp/native_benchmark_preflight/company12 --json`
5. run one reliability suite smoke into /tmp, for example:
   - `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py eval run --suite recovery6 --output-root /tmp/native_benchmark_preflight/recovery6 --json`
6. run the current local release smoke into /tmp if practical:
   - `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_local_release_smoke.py --output-root /tmp/native_benchmark_preflight/release --json`
7. check `git status --short` after the /tmp runs to ensure the repo remains clean

If a command is too expensive or blocked, record that clearly and explain why.

F. What the audit report must contain
`.agent/native_benchmark/PREFLIGHT_NATIVE_BENCHMARK_AUDIT.md` must contain exactly these sections:

1. Summary
2. Checked files and commands
3. Current native benchmark inventory
4. Current tier classification by suite
5. Current reusable metrics and artifacts
6. Configuration and local-asset findings
7. Missing pieces for regression-tier native benchmark
8. Missing pieces for provider-backed full native benchmark
9. Blockers
10. Recommended next step
11. Readiness verdict

G. What `.agent/native_benchmark/STATUS.md` must contain
Include:
- run start time
- commands actually run
- outputs/paths used under /tmp
- suite rerun results
- local asset findings
- blockers
- final readiness verdict

H. Decision rules
- If current smoke reruns cleanly, but regression/full-native work still lack clear prerequisites or implementation readiness, return `READY_FOR_CURRENT_SMOKE`
- If smoke reruns cleanly and there is no major blocker to starting native benchmark expansion work, return `READY_FOR_NATIVE_REGRESSION_EXPANSION`
- Only return `READY_FOR_PROVIDER_BACKED_FULL_NATIVE_RUN` if provider-backed native runs are truly configuration-ready right now
- Return `NOT_READY` if the current native benchmark cannot even be safely rerun or if critical preconditions are missing

I. Output discipline
While working, continuously print:
- what you are checking
- why it matters
- which files you read
- which commands you ran
- what passed or failed
- what is blocked
- what verdict is becoming likely

Completion rules:
- stop after the preflight audit is complete
- do not start implementation
- do not create worktrees
- do not merge branches
- finish by printing:
  - readiness verdict
  - top blockers
  - top reusable assets
  - exact next step