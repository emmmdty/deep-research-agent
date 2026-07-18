# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

面向科研与行业分析的 evidence-first 多 agent 研究产品：用可审计报告 bundle 交付结论，而不是只输出一次性聊天答案。

## 核心架构

- `src/deep_research_agent/gateway/`：CLI、本地 HTTP API、batch 命令和 artifact 访问。
- `src/deep_research_agent/research_jobs/`：确定性 job 生命周期，支持 checkpoint、event、cancel、retry、resume、refine。
- `src/deep_research_agent/connectors/`：web、GitHub、arXiv、文件接入，经过 source policy 和 snapshot。
- `src/deep_research_agent/auditor/`：claim graph、support edge、conflict set、audit decision、review queue。
- `src/deep_research_agent/reporting/`：report bundle 编译和 sidecar artifact 输出。
- `src/deep_research_agent/providers/`：OpenAI、Anthropic 和 compatible provider routing。
- `src/deep_research_agent/product/`：PostgreSQL-backed topic、conversation、run、memory 与租户边界。
- `src/deep_research_agent/corpus/`：受治理的论文接入、不可变 manifest、解析器 fallback 与公共内容缓存。
- `src/deep_research_agent/observability/`：不含凭据的 OpenTelemetry span 和 Phoenix 导出。

`src/deep_research_agent/` 是唯一 canonical runtime。根目录下 `services/`、`connectors/`、`artifacts/`、`policies/`、`tools/`、`evaluation/` 等目录是 compatibility 或 diagnostic layer。完整分类见 [仓库地图](./docs/REPO_MAP.md)。

## Repository Layout

```text
src/deep_research_agent/  canonical runtime
apps/gui-web/             可选本地 reviewer UI
docker-compose.yml        V2 API、Web、worker、PostgreSQL/pgvector、MinIO、GROBID、Phoenix
apps/desktop-tauri/       实验性 desktop wrapper
configs/                  runtime 与 source profile 配置
schemas/                  JSON artifact 与 runtime contract
evals/                    deterministic eval 资产和报告
docs/                     reviewer 文档和 archive
tests/                    回归测试
scripts/                  smoke、eval、diagnostic 命令
legacy/                   已归档 graph-first 路径
```

## 快速运行

```bash
uv sync --group dev
cp .env.example .env
uv run python main.py --help
```

## V2 Web Demo

支持的产品路径是带认证的 V2 workspace。复制 `.env.example` 并替换所有占位密钥；想运行
无需 provider 凭据的确定性 demo 时使用 `SCHEDULER_RUNTIME_MODE=offline`，然后执行。offline 模式
只验证认证、意图路由、任务持久化、SSE、报告渲染、语料冻结和记忆生命周期，不访问网络，也不会
伪造有证据的结论：

```bash
docker compose up --build
```

打开 `http://127.0.0.1:8000`。Web 容器是同源入口，并把 API 与 SSE 代理到内部服务。生产模式
必须配置真实的 `SCHEDULER_FACTORY_PATH`，不会静默降级到 offline。

如果只在单机上运行持久化 Demo，可以不启动 Docker/PostgreSQL，使用文件型 SQLite 和 Web 注册：

```bash
PRODUCT_DATABASE_URL=sqlite+pysqlite:///./workspace/product.db \\
PRODUCT_OFFLINE_MODE=true \\
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

产品数据库文件会保存账号、会话、主题、运行记录、记忆和语料元数据；`workspace/` 会保存持久化
任务与报告工件，重启服务后仍然保留。公开注册只在 `PRODUCT_OFFLINE_MODE=true` 时开启，PostgreSQL
Compose profile 仍然使用邀请制。

提交一个不启动 worker 的本地 job：

```bash
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --no-worker \
  --json
```

启动本地 API：

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

核心 smoke：

```bash
uv run python main.py --help
uv run ruff check .
uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
```

## Artifact Contract

完成态 job 会写入 `workspace/research_jobs/<job_id>/`。

稳定 artifact 名称：

- `report_bundle.json`：权威机器可读输出
- `report.md`、`report.html`：面向阅读的渲染结果
- `claims.json`、`sources.json`、`audit_decision.json`、`review_queue.json`、`claim_graph.json`：审计 sidecar
- `trace.jsonl`、`manifest.json`、`review_actions.jsonl`：执行和 review 记录

CLI 读取 artifact：

```bash
uv run python main.py bundle --job-id <job_id> --json
```

本地 API 读取 artifact：

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/artifacts/report_bundle.json
```

## Evaluation Summary

权威 merge-safe gate 是 `evals/reports/phase5_local_smoke/` 下的本地 deterministic smoke pack。面向 reviewer 的 deterministic regression evidence 位于 `evals/reports/native_regression/` 和 [docs/benchmarks/native](./docs/benchmarks/native/README.md)。

当前 committed value scorecard 中的关键指标：

- completion rate: `1.0`
- bundle emission rate: `1.0`
- critical claim support precision: `1.0`
- citation error rate: `0.0`
- policy compliance rate: `1.0`
- resume success rate: `1.0`

详见 [Experiment Summary](./docs/final/EXPERIMENT_SUMMARY.md) 和 [Value Scorecard](./docs/final/VALUE_SCORECARD.md)。

## 本地 UI

可选 reviewer/operator UI 位于 `apps/gui-web/`，消费本地 API。

```bash
cd apps/gui-web
npm install
npm run dev
```

本地 Vite 开发时设置 `VITE_DRA_API_BASE_URL` 指向 API，并为跨端口开发配置明确的 API origin。
Compose 使用同源代理，因此浏览器凭据和 SSE 重连不需要 wildcard CORS。

## 支持的问题与数据源边界

第一版领域包聚焦事件图谱、agent、LLM 如何相互作用。用户可以请求有来源的综述、方法或论文
比较、精确 claim-to-span 证据、矛盾审查和显式刷新。对于昂贵或信息不足的任务，API 会先要求
澄清；未刷新前的追问使用冻结报告快照。

关键 claim 仅能使用受治理且已冻结的来源：arXiv、ACL Anthology、OpenAlex、Crossref、DataCite、
DBLP、PMLR、NeurIPS proceedings 以及有许可证的上传文档。这是来源策略目标，不代表这些连接器
已经全部接入产品。当前产品 API 支持显式选择租户上传文档并在运行前冻结路径和哈希；内置 connector
substrate 提供 arXiv、GitHub、开放 Web 和本地文件适配器，ACL Anthology、OpenAlex、Crossref、
DataCite、DBLP、PMLR、NeurIPS 仍是后续集成项。开放 Web 搜索只能用于发现，不能支撑关键 claim。

可选 desktop packaging 实验位于 `apps/desktop-tauri/`。详见 [GUI docs](./docs/gui/README.md)。

## 当前限制

- Docker profile 面向小团队，不是横向扩展的 SaaS control plane。
- Runtime 仍使用 job-local subprocess 和 recovery worker，没有 Redis queue。
- Live research 需要显式配置 `SCHEDULER_FACTORY_PATH`；仓库不会把 offline demo 静默变成实时爬虫。
- 记忆当前是显式 CRUD 加按主题/会话的运行时召回；对话不会自动写入长期记忆，Web 页面暂时只有查看和删除。
- Legacy comparator 与 report-shape diagnostics 仍可用于诊断，但 release story 是 claim-centric bundle/eval 输出。
- 这不是多租户 SaaS，也不是“agent 越多越好”的展示项目。

## Roadmap

- 先运行并测量当前 PostgreSQL/MinIO profile，再决定是否引入外部 queue/object-storage adapter。
- 扩展 claim-support evaluation，超过 deterministic smoke/regression 套件。
- 用 capability、health、cost、rate limit 信号强化 provider routing。
- 改进 human review flow，使 review decision 能重新编译或显式标注 bundle。
- 持续把 legacy diagnostic code 移出公开产品主路径。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
