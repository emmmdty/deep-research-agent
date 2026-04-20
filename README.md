# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

English | [简体中文](./README.zh-CN.md)

A LangGraph-based deep research agent project focused on multi-source evidence gathering, structured evaluation, and comparator-driven benchmarking.

## Project Positioning

This repository is maintained as a public research-engineering / portfolio project.

It is designed to show:

- a multi-agent deep research workflow
- structured evidence and citation handling
- benchmark and comparator harnesses
- testable, documented engineering decisions

The supported public surface is CLI-first. Phase 02 exposes a job-oriented CLI (`submit / status / watch / cancel / retry`). There is currently no supported HTTP API.
Phase 03 extends that runtime with a unified connector substrate, source policy, and snapshot store. Public jobs now collect fetched documents through `search / fetch / file-ingest` contracts before they become research evidence.
Phase 04 adds a claim-level audit pipeline after extraction. Public jobs now emit claim graph artifacts and may finish as `completed` with `audit_gate_status=blocked` when critical claims remain unresolved.

## Features

- Hierarchical workflow: `Supervisor -> Planner -> Researcher -> Verifier -> Critic -> Writer`
- Multi-source research with `web`, `github`, and `arxiv`
- Capability registry with `builtin / skill / mcp` routing
- Structured artifacts: `SourceRecord`, `EvidenceNote`, `EvidenceUnit`, `VerificationRecord`, `RunMetrics`, `ReportArtifact`
- Benchmark runner and full comparator harness
- Benchmark profile uses a strict `quality_gate`: if the final loop still fails the gate, the workflow terminates as failure instead of emitting a pseudo-complete report
- Case-study aspects are treated as production evidence tasks and only count `official + first-party repo` evidence; surveys and generic blogs do not pass the gate
- Case-study retrieval now uses query bundles with `site:` official-domain expansion, first-party GitHub repo search, and dedicated rescue queries instead of a single generic query
- Benchmark summary with `scorecard + legacy_metrics + judge_status`, so reliability signals are shown as 0-100 continuous scores instead of only boolean / 0-1 fields
- `portfolio12` topic set and `run_ablation.py` for reproducible method comparisons
- Blind pairwise report judging through `LLM-as-Judge`
- Phase 02 resumable job runtime with SQLite-backed status, events, checkpoints, cancel, retry, and stale-job recovery
- Phase 03 connector substrate with unified `search / fetch / file-ingest`, snapshot persistence, domain allow/deny enforcement, and per-job fetch budgets
- Phase 04 claim-level audit pipeline with `claim_auditing`, claim graph, conflict sets, and critical-claim review queue
- Completed jobs emit `report.md`, `report_bundle.json`, `trace.jsonl`, fetched `snapshots/`, and `audit/` artifacts under `workspace/research_jobs/<job_id>/`

## Quickstart

### 1. Install dependencies

```bash
uv sync --group dev
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Fill in the required API keys before running research commands.

### 3. Submit and watch a research job

```bash
uv run python main.py submit \
  --topic "Latest progress in LLM agent architectures" \
  --source-profile trusted-web \
  --allow-domain github.com \
  --allow-domain docs.langchain.com \
  --max-candidates-per-connector 4 \
  --max-fetches-per-task 3 \
  --max-total-fetches 8
uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
```

The public CLI now submits background jobs. Completed jobs write `report.md`, `report_bundle.json`, `trace.jsonl`, `snapshots/`, and `audit/` into `workspace/research_jobs/<job_id>/`.
If critical claims remain unsupported or contradicted, the job still completes but surfaces `audit_gate_status=blocked`.

### 4. Run benchmark and comparison commands

```bash
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set portfolio12 --summary
uv run python scripts/run_ablation.py --topic-set portfolio12 --profile benchmark
uv run python scripts/run_portfolio12_release.py --env-file /absolute/path/.env --topic-set portfolio12 --release-mode hybrid
uv run python scripts/optimize_local3.py --profile benchmark --max-rounds 3 --skip-judge
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba
uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md
```

`benchmark_summary.json` now exposes two layers:
- `scorecard`: product-facing 0-100 scores for research reliability, system controllability, report quality, and evaluation reproducibility
- `legacy_metrics`: compatibility aggregates for older fields such as `aspect_coverage`, `citation_accuracy`, and `depth_score`
- `benchmark_health`: completion, gate pass rate, judge status, and resilience signals for honest experiment reporting
- Case-study outputs now additionally expose `case_study_strength_score_100`, `first_party_case_coverage_100`, `official_case_ratio_100`, and `case_study_gate_margin_100`

For a release-grade `portfolio12` bundle, prefer `scripts/run_portfolio12_release.py`. The default `--release-mode hybrid` runs live judge on representative topics (`T01,T04,T11`) and keeps the full `portfolio12` benchmark / ablation reproducible; use `--env-file` to load the environment with live judge and search credentials.

## Example Output

Representative CLI flow:

```text
$ uv run python main.py submit --topic "Latest progress in LLM agent architectures"
✅ 已提交 job: 20260409T120000Z-abc12345
当前状态: created -> next: clarifying

$ uv run python main.py watch --job-id 20260409T120000Z-abc12345
[0002] clarifying stage.started - 开始 clarifying 阶段
[0012] claim_auditing stage.completed - claim_auditing 阶段完成
[0015] rendering stage.completed - rendering 阶段完成
[0016] completed job.completed - job 进入 completed
```

## Configuration

Publicly supported environment variables include:

- `LLM_PROVIDER`
- `LLM_MODEL_NAME`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `SEARCH_BACKEND`
- `TAVILY_API_KEY`
- `MAX_RESEARCH_LOOPS`
- `MAX_SEARCH_RESULTS`
- `RESEARCH_PROFILE`
- `RESEARCH_CONCURRENCY`
- `ENABLED_CAPABILITY_TYPES`
- `SKILL_PATHS`
- `MCP_CONFIG_PATH`
- `MCP_SERVERS`
- `CASE_STUDY_OFFICIAL_DOMAINS`
- `ENABLED_SOURCES`
- `ENABLED_COMPARATORS`
- `BUNDLE_EMISSION_ENABLED`
- `BUNDLE_OUTPUT_DIRNAME`
- `JOB_RUNTIME_DIRNAME`
- `JOB_HEARTBEAT_INTERVAL_SECONDS`
- `JOB_STALE_TIMEOUT_SECONDS`
- `LEGACY_CLI_ENABLED`
- `SOURCE_POLICY_MODE`
- `CONNECTOR_SUBSTRATE_ENABLED`
- `SNAPSHOT_STORE_DIRNAME`
- `MEMORY_BACKEND`
- `JUDGE_MODEL`
- `GPT_RESEARCHER_PYTHON`
- `OPEN_DEEP_RESEARCH_COMMAND`
- `OPEN_DEEP_RESEARCH_REPORT_DIR`
- `ALIBABA_RUNNER_MODE`
- `ALIBABA_COMMAND`
- `ALIBABA_REPORT_DIR`
- `GEMINI_ENABLED`
- `GEMINI_ALLOWLIST_REQUIRED`
- `GEMINI_COMMAND`
- `GEMINI_REPORT_DIR`

See [`.env.example`](./.env.example) for the complete template.

## Repository Layout

```text
agents/       multi-agent nodes, including verifier
services/research_jobs/ SQLite-backed public job runtime
connectors/   unified search / fetch / file-ingest substrate and adapters
policies/     source profiles, budget guardrails, and domain governance
capabilities/ builtin / skill / mcp capability registry and adapters
tools/        search and utility tools
workflows/    state graph and structured state models
evaluation/   metrics, judge, cost tracking, comparator registry
memory/       sqlite-backed evidence memory
scripts/      benchmark, comparison, and offline comparison commands
tests/        regression and unit tests
docs/         architecture and development notes
```

## Development

Local verification:

```bash
uv run ruff check .
uv run pytest -q
```

Phase 01 live validation:

```bash
WORKSPACE_DIR=workspace/phase1-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py legacy-run --topic "Datawhale是一个什么样的组织" --max-loops 2
```

Then inspect the emitted Markdown and sidecar bundle under `workspace/phase1-live-validation/`.

Phase 02 live validation:

```bash
WORKSPACE_DIR=workspace/phase2-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py submit --topic "Datawhale是一个什么样的组织"
uv run python main.py watch --job-id <job_id>
```

Phase 03 live validation:

```bash
WORKSPACE_DIR=workspace/phase3-live-validation \
ENABLED_SOURCES='["github"]' \
uv run python main.py submit \
  --topic "langgraph github repository" \
  --source-profile trusted-web \
  --allow-domain github.com \
  --max-candidates-per-connector 3 \
  --max-fetches-per-task 2 \
  --max-total-fetches 4
uv run python main.py watch --job-id <job_id>
```

Phase 04 audit regression:

```bash
uv run pytest -q tests/test_phase4_auditor.py
```

If you override list settings directly from the shell, prefer JSON-array syntax such as `ENABLED_SOURCES='["github"]'`.

Key developer docs:

- [Architecture](./docs/architecture.md)
- [Development Guide](./docs/development.md)
- [Contributing](./CONTRIBUTING.md)
- [Security Policy](./SECURITY.md)

## Limitations

- Comparator integrations such as `odr`, `alibaba`, and `gemini` still depend on your configured command templates or imported report directories.
- MCP support is file-first and capability-first: v1 supports `stdio` / `sse` / `streamable-http` server discovery, cache, and routing through the capability layer. External server behavior still depends on each server's published schema and auth requirements.
- The repository intentionally does not expose a supported HTTP server surface in the current version.

## License

MIT. See [LICENSE](./LICENSE).
