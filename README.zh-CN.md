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

当前公开支持的入口是 CLI。phase2 以后，公开命令面改为 `submit / status / watch / cancel / retry`，仍不提供受支持的 HTTP API。
phase3 在此基础上接入了统一 connector substrate、source policy 和 snapshot store，公开 job 会先走 `search / fetch / file-ingest` 合同，再把抓取后的文档转成研究证据。
phase4 在 `extracting` 后增加了 claim-level audit pipeline。公开 job 会额外输出 claim graph / review queue，且在关键 claim 未解决时使用 `completed + blocked` 语义。

## 主要能力

- 分层工作流：`Supervisor -> Planner -> Researcher -> Verifier -> Critic -> Writer`
- 默认多源研究：`web`、`github`、`arxiv`
- `builtin / skill / mcp` 统一 capability registry 与任务路由
- 结构化状态对象：`SourceRecord`、`EvidenceNote`、`EvidenceUnit`、`VerificationRecord`、`RunMetrics`、`ReportArtifact`
- 统一 benchmark 与 comparator 入口
- benchmark profile 采用严格 `quality_gate`：最后一轮仍未达标时直接失败终止，不再输出伪完成报告
- `case-study / 行业应用案例` 方面会走专用检索与筛选链，只接受 `官方站点 + 一手仓库` 证据；综述、泛博客和背景文章不会通过 gate
- case-study 检索默认使用多模板 query bundle：官方域名 `site:` 扩展、GitHub 一手仓库搜索、以及失败后的 rescue queries
- `benchmark_summary.json` 采用 `scorecard + legacy_metrics + judge_status` 双层输出，对外主展示为 `0-100` 连续值可靠性分数
- `portfolio12` 主题集与 `run_ablation.py` 支持把项目方法点做成可复现的对照实验
- 基于 `LLM-as-Judge` 的盲评对比
- Phase 02 可恢复 job runtime：SQLite 持久化状态、event、checkpoint，支持 cancel / retry / stale job recovery
- Phase 03 统一 connector substrate：`search / fetch / file-ingest`、snapshot 持久化、domain allow/deny 和每 job 抓取预算
- Phase 04 claim-level audit pipeline：`claim_auditing`、claim graph、conflict set 与 critical claim review queue
- 完成态 job 会在 `workspace/research_jobs/<job_id>/` 下输出 `report.md`、`report_bundle.json`、`trace.jsonl`、`snapshots/` 和 `audit/`

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

### 3. 提交并观察研究任务

```bash
uv run python main.py submit \
  --topic "2024 年大语言模型 Agent 架构的最新进展" \
  --source-profile trusted-web \
  --allow-domain github.com \
  --allow-domain docs.langchain.com \
  --max-candidates-per-connector 4 \
  --max-fetches-per-task 3 \
  --max-total-fetches 8
uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
```

公开 CLI 现在会提交后台 job。完成态 job 会把 `report.md`、`report_bundle.json`、`trace.jsonl`、`snapshots/` 和 `audit/` 写到 `workspace/research_jobs/<job_id>/`。
如果关键 claim 仍未通过审计门禁，job 仍会完成，但会明确暴露 `audit_gate_status=blocked`。

### 4. 运行 benchmark / 对比

```bash
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set portfolio12 --summary
uv run python scripts/run_ablation.py --topic-set portfolio12 --profile benchmark
uv run python scripts/run_portfolio12_release.py --env-file /绝对路径/.env --topic-set portfolio12 --release-mode hybrid
uv run python scripts/optimize_local3.py --profile benchmark --max-rounds 3 --skip-judge
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba
uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md
```

其中 `benchmark_summary.json` 现在分成两层：
- `scorecard`：面向展示的 `0-100` 分数卡，包含研究可靠性、系统可控性、报告质量、评测可复现性
- `legacy_metrics`：保留旧字段聚合结果，兼容历史脚本与结果对比
- `benchmark_health`：补充展示完成率、质量门控通过率、judge 状态与恢复韧性
- case-study 相关连续值指标还包括：`case_study_strength_score_100`、`first_party_case_coverage_100`、`official_case_ratio_100`、`case_study_gate_margin_100`

如果需要把 `portfolio12` 的 benchmark、ablation 与 `RESULTS.md` 一次打包成可复用诊断结果集，使用 `scripts/run_portfolio12_release.py`。默认 `--release-mode hybrid` 会只对代表题 `T01,T04,T11` 运行 live judge，同时保留全量 `portfolio12` 的可复现实验输出；并通过 `--env-file` 显式加载带有 Judge/搜索密钥的环境文件。

Phase 05 增加了本地 release gate manifest。benchmark diagnostics 是必需项，但不能单独证明产品可发布；gate 还要求 runtime recovery、connector security、claim audit grounding 和公开 surface 文档检查。当前这只是本地 checklist / manifest，不是外部 CI 或生产监控系统。

## 示例输出

一个典型的 CLI 运行过程大致如下：

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

完整模板见 [`.env.example`](./.env.example)。

## 仓库结构

```text
agents/       多智能体节点，包含 verifier
services/research_jobs/ SQLite 持久化公开 job runtime
connectors/   统一 search / fetch / file-ingest substrate 与适配层
policies/     source profile、budget guardrail 与 domain 治理
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

Phase 01 联网验收可直接使用：

```bash
WORKSPACE_DIR=workspace/phase1-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py legacy-run --topic "Datawhale是一个什么样的组织" --max-loops 2
```

然后检查 `workspace/phase1-live-validation/` 下的 Markdown 与 `bundles/<run_id>/` 侧车产物。

Phase 02 联网验收可直接使用：

```bash
WORKSPACE_DIR=workspace/phase2-live-validation \
ENABLED_SOURCES='["web"]' \
uv run python main.py submit --topic "Datawhale是一个什么样的组织"
uv run python main.py watch --job-id <job_id>
```

Phase 03 联网验收可直接使用：

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

Phase 04 审计回归可直接使用：

```bash
uv run pytest -q tests/test_phase4_auditor.py
```

如果直接在 shell 中覆盖列表配置，建议使用 JSON 数组形式，例如 `ENABLED_SOURCES='["github"]'`。

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
