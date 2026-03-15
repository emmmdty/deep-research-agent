# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

这是一个基于 LangGraph 的深度研究 Agent 项目，重点展示多智能体工作流、多源证据采集、结构化评测，以及 comparator 驱动的 benchmark 工程化能力。

## 项目定位

该仓库当前按公开的研究工程 / 作品集项目维护，目标不是做成一个完整产品，而是展示：

- 多智能体深度研究流程
- 结构化证据与引用建模
- benchmark 与 comparator harness
- 可测试、可解释、可维护的工程实现

当前公开支持的入口是 CLI，不提供受支持的 HTTP API。

## 主要能力

- 多智能体工作流：`Supervisor -> Planner -> Researcher -> Critic -> Writer`
- 默认多源研究：`web`、`github`、`arxiv`
- 结构化状态对象：`SourceRecord`、`EvidenceNote`、`RunMetrics`、`ReportArtifact`
- 统一 benchmark 与 comparator 入口
- 基于 `LLM-as-Judge` 的盲评对比

## 快速开始

### 1. 安装依赖

```bash
uv sync --group dev
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

补齐 API Key 后再运行研究或 benchmark。

### 3. 运行研究

```bash
uv run python main.py --topic "2024 年大语言模型 Agent 架构的最新进展"
```

### 4. 运行 benchmark / 对比

```bash
uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba
uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md
```

## 示例输出

一个典型的 CLI 运行过程大致如下：

```text
$ uv run python main.py --topic "Latest progress in LLM agent architectures"
🚀 启动深度研究: topic='Latest progress in LLM agent architectures', max_loops=3
📋 Planner 规划完成: 生成 4 个子任务
🔍 Researcher 执行完成: 总结数=4, 来源数=12
🧠 Critic 评分完成: quality_score=8, is_sufficient=True
📝 Writer 报告生成完成
🎉 深度研究完成: status=completed
```

## 配置项

公开支持的环境变量包括：

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

完整模板见 [`.env.example`](./.env.example)。

## 仓库结构

```text
agents/       多智能体节点
tools/        搜索与工具适配
workflows/    状态图与结构化状态
evaluation/   指标、Judge、成本统计、Comparator 协议
scripts/      benchmark、对比与离线比较命令
tests/        回归测试与单元测试
docs/         架构与开发文档
```

## 开发与验证

```bash
uv run ruff check .
uv run pytest -q
```

相关文档：

- [架构设计](./docs/architecture.md)
- [开发指南](./docs/development.md)
- [贡献指南](./CONTRIBUTING.md)
- [安全策略](./SECURITY.md)

## 当前限制

- `gptr` comparator 依赖隔离 Python 环境，例如 `GPT_RESEARCHER_PYTHON` 或本地 `venv_gptr`。
- `odr`、`alibaba` comparator 仍依赖你本地配置的命令模板或报告导入目录。
- `gemini` 是可选 comparator，默认不启用，允许返回 `skipped`。
- `memory/`、`skills/`、`mcp_servers/` 当前不属于默认 CLI 主工作流的公开能力面。
- 当前版本不提供受支持的 HTTP 服务接口。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
