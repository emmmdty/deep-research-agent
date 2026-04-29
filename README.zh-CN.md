# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

面向公司/行业分析的 evidence-first 研究运行时：用可审计 job 和 artifact bundle 交付结论，而不是只输出一次性聊天答案。

## 核心架构

- `src/deep_research_agent/gateway/`：CLI、本地 HTTP API、batch 命令和 artifact 访问。
- `src/deep_research_agent/research_jobs/`：确定性 job 生命周期，支持 checkpoint、event、cancel、retry、resume、refine。
- `src/deep_research_agent/connectors/`：web、GitHub、arXiv、文件接入，经过 source policy 和 snapshot。
- `src/deep_research_agent/auditor/`：claim graph、support edge、conflict set、audit decision、review queue。
- `src/deep_research_agent/reporting/`：report bundle 编译和 sidecar artifact 输出。
- `src/deep_research_agent/providers/`：OpenAI、Anthropic 和 compatible provider routing。

`src/deep_research_agent/` 是唯一 canonical runtime。根目录下 `services/`、`connectors/`、`artifacts/`、`policies/`、`tools/`、`evaluation/` 等目录是 compatibility 或 diagnostic layer。完整分类见 [仓库地图](./docs/REPO_MAP.md)。

## 快速运行

```bash
uv sync --group dev
cp .env.example .env
uv run python main.py --help
```

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

Desktop packaging 实验位于 `desktop/tauri/`。详见 [GUI docs](./docs/gui/README.md)。

## 当前限制

- HTTP API 仍是本地 API：没有 auth、tenant isolation、external queue 或 object storage。
- Runtime storage 是 SQLite + filesystem artifacts。
- Live web research 依赖 provider/search credentials 和外部网络稳定性。
- Legacy comparator 与 report-shape diagnostics 仍可用于诊断，但 release story 是 claim-centric bundle/eval 输出。
- 这不是多租户 SaaS，也不是“agent 越多越好”的展示项目。

## Roadmap

- 推进 server profile：PostgreSQL、Redis Streams、S3-compatible object storage。
- 扩展 claim-support evaluation，超过 deterministic smoke/regression 套件。
- 用 capability、health、cost、rate limit 信号强化 provider routing。
- 改进 human review flow，使 review decision 能重新编译或显式标注 bundle。
- 持续把 legacy diagnostic code 移出公开产品主路径。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
