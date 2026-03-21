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

The supported public surface is CLI-first. There is currently no supported HTTP API.

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

### 3. Run a research task

```bash
uv run python main.py --topic "Latest progress in LLM agent architectures"
uv run python main.py --topic "OpenClaw installation guide" --profile benchmark
```

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

Interview-oriented materials are included in:

- `docs/showcase.md`
- `docs/resume_bullets.md`
- `docs/interview_qa.md`

## Example Output

Representative CLI flow:

```text
$ uv run python main.py --topic "Latest progress in LLM agent architectures"
🚀 启动深度研究: topic='Latest progress in LLM agent architectures', max_loops=3
📋 Planner 规划完成: 生成 4 个子任务
🔍 Researcher 执行完成: 总结数=4, 来源数=12
🧠 Critic 评分完成: quality_score=8, is_sufficient=True
📝 Writer 报告生成完成
🎉 深度研究完成: status=completed
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
