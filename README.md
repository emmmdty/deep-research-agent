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

- Multi-agent workflow: `Supervisor -> Planner -> Researcher -> Critic -> Writer`
- Multi-source research with `web`, `github`, and `arxiv`
- Structured artifacts: `SourceRecord`, `EvidenceNote`, `RunMetrics`, `ReportArtifact`
- Benchmark runner and full comparator harness
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
```

### 4. Run benchmark and comparison commands

```bash
uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba
uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md
```

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
- `RESEARCH_CONCURRENCY`
- `ENABLED_SOURCES`
- `ENABLED_COMPARATORS`
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
agents/       multi-agent nodes
tools/        search and utility tools
workflows/    state graph and structured state models
evaluation/   metrics, judge, cost tracking, comparator registry
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

- The `gptr` comparator depends on an isolated Python environment such as `GPT_RESEARCHER_PYTHON` or a local `venv_gptr`.
- Comparator integrations such as `odr` and `alibaba` still depend on your configured command templates or imported report directories.
- `gemini` is an optional comparator, disabled by default, and may return `skipped`.
- `memory/`, `skills/`, and `mcp_servers/` are not part of the default public CLI workflow surface.
- The repository intentionally does not expose a supported HTTP server surface in the current version.

## License

MIT. See [LICENSE](./LICENSE).
