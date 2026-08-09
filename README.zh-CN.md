# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://emmmdty.github.io/deep-research-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

**Evidence-first 的多 agent 深度研究系统**：把一次研究任务编译成任务 DAG，通过受治理的模型/工具网关并行运行 researcher 与 critic agent，对冻结证据库逐条审计关键 claim，最终交付可审计的报告 bundle —— 而不是一个聊天式答案。

## 为什么值得看

2025 年深度研究赛道爆发（OpenAI Deep Research、Gemini、Perplexity、STORM…）。这个项目问了一个不同的问题：**当答案错了，你能证明吗？**

- **多 agent 且被测量** —— 并行 researcher + critic agent，运行在有界 DAG 调度器上；每个组件的价值由确定性消融实验证明，而不是口头宣称。
- **Evidence-first 输出** —— 交付物是机器可读的报告 bundle：每条关键 claim 都携带指向冻结不可变 corpus manifest 的证据片段。
- **生产级可靠性** —— checkpoint 化 job 可承受 cancel/retry/resume/stale 恢复；claim graph、审计门禁、人工复核队列都是一等公民产物。

[在线 Demo](https://emmmdty.github.io/deep-research-agent/) · [竞品分析](./docs/final/COMPETITIVE_LANDSCAPE.md) · [仓库地图](./docs/REPO_MAP.md)

## 架构总览

![Deep Research Agent user-facing architecture](./docs/assets/architecture-overview.png)

canonical runtime 位于 `src/deep_research_agent/`：

| 层 | 模块 | 职责 |
| --- | --- | --- |
| Agent 编排 | `orchestration/`（`dag.py`、`scheduler.py`、`workers.py`、`reducer.py`） | 把研究 brief 编译成不可变任务 DAG；有界 asyncio 调度器并行执行就绪任务（≤8 worker），类型化消息传递 |
| Agent 角色 | `ResearchPlanner`（researcher）、critic 任务（`CriticDecision`） | 每个 objective 一个并行 research 任务；critic 审计依赖输出并给出 accepted/qualified/contradicted/unresolved 决策 |
| 治理 | `tool_gateway/`、`model_runtime/`、`policy/` | 角色白名单、幂等、缓存、预算上限、重试；按角色模型 fallback 链 + AES-GCM 凭据 |
| 证据与审计 | `auditor/`、`evidence_store/`、`corpus/` | 带 support edge 的 claim graph、冲突集、复核队列；冻结 corpus manifest；来源快照 |
| 交付 | `reporting/bundle_v2.py` | 确定性归并 → 审计 → `report_bundle.json`（+ `report.md/html`）与 sidecar 产物 |
| 可靠性 | `research_jobs/`、`observability/` | checkpoint、事件、lease、心跳、resume/retry/refine；不含凭据的 OpenTelemetry span |
| 产品面 | `gateway/`、`product/`、`apps/gui-web/` | CLI、本地 HTTP API（SSE 事件流）、PostgreSQL 多租户产品 API、React workspace UI |

根目录下 `services/`、`connectors/`、`artifacts/`、`policies/`、`tools/`、`evaluation/` 等是
compatibility 或 diagnostic layer。完整分类见 [仓库地图](./docs/REPO_MAP.md)。

## 一次研究任务的运行流程

```
user topic → ResearchPlanner.plan() → ResearchDAG（research 任务 ∥ critic 任务）
   → ResearchScheduler.run() [有界 asyncio，≤8 workers，类型化 TaskSpec/WorkerOutput]
   → ToolGateway（受治理检索）→ ModelRegistry（角色 fallback 链）
   → EvidenceReducer.reduce() → EvidenceAuditor.audit()
   → ReportBundleCompilerV2.compile() → report_bundle.json + report.md/html
   → 产物落盘 workspace/research_jobs/<job_id>/
```

bundle 中每条关键 claim 必须解析到冻结 corpus manifest 内的证据片段；无法验证的 claim 进入
人工复核队列。完整生命周期见 [docs/architecture.md](./docs/architecture.md) 与
[docs/USER_GUIDE.md](./docs/USER_GUIDE.md)。

## 评测与 Benchmark 证据

发布门禁是确定性的、本地可复现 —— 无需 API key、无需网络：

| 证据 | 位置 | 结果 |
| --- | --- | --- |
| 权威 smoke gate | `evals/reports/phase5_local_smoke/` | 5 个 suite × smoke_local，全部 passed |
| 原生回归 | `evals/reports/native_regression/` | company12/industry12/trusted8/file8/recovery6 passed |
| 核心指标 | `evals/reports/followup_metrics/headline_metrics.json` | completion rate 1.0、critical claim support precision 1.0、citation error rate 0.0 |
| 消融实验（多 agent 价值） | `evals/reports/followup_metrics/ablation_summary.md` | 见下表 |
| 外部 benchmark 适配器 | `evals/external/` + `portfolio_summary.json` | BrowseComp/GAIA/LongBench-v2/LongFact/Facts grounding guarded smoke |
| 价值计分卡 | [docs/final/VALUE_SCORECARD.md](./docs/final/VALUE_SCORECARD.md) | 完整指标定义与结果 |

### 消融证据：每个组件为什么存在

确定性消融证明每个机制都有可测量的因果贡献：

| 消融 | 移除后的退化 |
| --- | --- |
| 审计门禁（`audit_on_vs_off`） | unsupported claim leakage → 1.0 |
| Evidence-first 综合（`evidence_first_vs_baseline`） | citation error rate → 1.0，来源完整性下降 |
| Rerank/边选择（`rerank_on_vs_off`） | critical claim support precision 1.0 → 0.5 |
| 严格来源策略（`strict_source_policy_vs_relaxed`） | policy compliance 1.0 → 0.333 |

本地一键复现：

```bash
uv sync --group dev
uv run python main.py eval run --suite company12 --variant smoke_local
uv run python main.py benchmark run --help
```

## 竞争定位

2025 深度研究格局：闭源产品（OpenAI、Gemini、Perplexity）交付"事后引用"的报告；开源框架
（STORM、LangChain open_deep_research、smolagents）缺少审计链。本项目差异化在**可审计性与
受治理的证据** —— 与 Anthropic 多 agent 研究系统博客点名的行业痛点（引用归属、来源质量、
checkpoint/恢复）完全对应。完整有据可查的对比见 [docs/final/COMPETITIVE_LANDSCAPE.md](./docs/final/COMPETITIVE_LANDSCAPE.md)。

## 快速开始

```bash
uv sync --group dev
cp .env.example .env        # 离线 demo 不需要任何密钥
uv run python main.py --help

uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --json
```

本地 Web demo（无 Docker、文件型 SQLite、离线确定性模式）：

```bash
PRODUCT_DATABASE_URL=sqlite+pysqlite:///./workspace/product.db \
PRODUCT_OFFLINE_MODE=true \
uv run uvicorn deep_research_agent.gateway.api:app --reload
# 另开终端
npm run dev --prefix apps/gui-web    # 打开 http://127.0.0.1:5173
```

完整 Compose profile（PostgreSQL/pgvector + MinIO + GROBID + Phoenix），无凭据离线调度器：

```bash
docker compose up --build     # 打开 http://127.0.0.1:8000
```

真实网络研究需要显式配置 `SCHEDULER_FACTORY_PATH`；运行时永远不会从生产模式静默回退到离线。

## Artifact Contract

完成态 job 写入 `workspace/research_jobs/<job_id>/`：

- `report_bundle.json` —— 权威机器可读输出
- `report.md`、`report.html` —— 面向阅读的渲染
- `claims.json`、`sources.json`、`audit_decision.json`、`review_queue.json`、`claim_graph.json` —— 审计 sidecar
- `trace.jsonl`、`manifest.json`、`review_actions.jsonl` —— 执行与复核记录

```bash
uv run python main.py bundle --job-id <job_id> --json
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
```

## Repository Layout

```text
src/deep_research_agent/  canonical runtime（orchestration、auditor、reporting、product...）
apps/gui-web/             React workspace UI（报告、证据、claim graph、记忆、admin）
apps/demo-site/           静态 GitHub Pages demo（报告浏览器、claim graph、trace 回放）
configs/                  runtime 与 source profile 配置
evals/                    确定性评测资产、报告与 fixtures
docs/                     reviewer 文档（索引、架构、benchmark、final）
tests/                    回归测试
scripts/                  smoke、eval、diagnostic 命令
legacy/                   已归档 graph-first runtime（orchestrator-v1 兼容路径）
```

## 当前限制

- 部署形态是小团队 Compose 栈，不是横向扩展的 SaaS control plane。
- 确定性评测是权威 gate；live provider 质量/成本对比是 roadmap。
- 开放 Web 搜索只能用于发现；关键 claim 仅限受治理的冻结来源。
- 记忆是显式 CRUD 加按主题召回；对话自动写入长期记忆是 roadmap。

## Roadmap

- 在 PostgreSQL/MinIO profile 上实测后，再引入 queue/object-storage adapter。
- Live provider 正面对比（ours vs open_deep_research vs gpt-researcher），带成本与质量遥测。
- 扩大 GAIA/BrowseComp 受保护子集覆盖；先审查 integrity findings 再扩展。
- 人工复核流程支持对已交付 bundle 重新编译或显式标注。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
