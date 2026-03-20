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

- 分层工作流：`Supervisor -> Planner -> Researcher -> Verifier -> Critic -> Writer`
- 默认多源研究：`web`、`github`、`arxiv`
- `builtin / skill / mcp` 统一 capability registry 与任务路由
- 结构化状态对象：`SourceRecord`、`EvidenceNote`、`EvidenceUnit`、`VerificationRecord`、`RunMetrics`、`ReportArtifact`
- 统一 benchmark 与 comparator 入口
- `benchmark_summary.json` 采用 `scorecard + legacy_metrics + judge_status` 双层输出，对外主展示为 `0-100` 连续值可靠性分数
- `portfolio12` 主题集与 `run_ablation.py` 支持把项目方法点做成可复现的对照实验
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
uv run python main.py --topic "openclaw安装教程" --profile benchmark
```

### 4. 运行 benchmark / 对比

```bash
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set portfolio12 --summary
uv run python scripts/run_ablation.py --topic-set portfolio12 --profile benchmark
uv run python scripts/optimize_local3.py --profile benchmark --max-rounds 3 --skip-judge
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba
uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md
```

其中 `benchmark_summary.json` 现在分成两层：
- `scorecard`：面向展示的 `0-100` 分数卡，包含研究可靠性、系统可控性、报告质量、评测可复现性
- `legacy_metrics`：保留旧字段聚合结果，兼容历史脚本与结果对比
- `benchmark_health`：补充展示完成率、质量门控通过率、judge 状态与恢复韧性

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
- `RESEARCH_PROFILE`
- `RESEARCH_CONCURRENCY`
- `ENABLED_CAPABILITY_TYPES`
- `SKILL_PATHS`
- `MCP_CONFIG_PATH`
- `MCP_SERVERS`
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

完整模板见 [`.env.example`](./.env.example)。

## 仓库结构

```text
agents/       多智能体节点，包含 verifier
capabilities/ builtin / skill / mcp 能力注册与适配
tools/        搜索与工具适配
workflows/    状态图与结构化状态
evaluation/   指标、Judge、成本统计、Comparator 协议
memory/       SQLite 持久化证据记忆
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

- `odr`、`alibaba`、`gemini` 等 comparator 仍依赖你本地配置的命令模板或报告导入目录。
- MCP 当前采用 file-first + capability-first 方式：v1 已支持 `stdio` / `sse` / `streamable-http` 三类 server 的发现、缓存与能力路由；但外部 server 的具体行为仍取决于其公开 schema 和鉴权要求。
- 当前版本不提供受支持的 HTTP 服务接口。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
