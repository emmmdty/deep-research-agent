# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

Deep Research Agent 是一个本地优先的研究运行时，适合公司和行业分析。它把研究任务作为可审计 job 运行，保存 checkpoint 和事件，并输出包含来源、claim、trace、review sidecar 的报告 bundle。

## 架构概览

![Deep Research Agent 用户向架构图](./docs/assets/architecture-overview.png)

## 安装

```bash
uv sync
cp .env.example .env
```

在 `.env` 中填写 LLM provider key，以及可选的 Tavily key。

## CLI

```bash
uv run python main.py --help
```

创建一个不启动 worker 的 job：

```bash
uv run python main.py submit \
  --topic "OpenAI company profile" \
  --source-profile company_trusted \
  --no-worker \
  --json
```

常用命令：

```bash
uv run python main.py status --job-id <job_id>
uv run python main.py watch --job-id <job_id>
uv run python main.py cancel --job-id <job_id>
uv run python main.py retry --job-id <job_id>
uv run python main.py resume --job-id <job_id>
uv run python main.py refine --job-id <job_id> --instruction "Focus on product revenue signals"
uv run python main.py bundle --job-id <job_id> --json
```

批量提交：

```bash
uv run python main.py batch run --file examples/batch_requests.json --json
```

## API

启动本地 API：

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

API 文档地址：`http://127.0.0.1:8000/docs`。

## Web UI

```bash
npm ci --prefix apps/gui-web
npm run dev --prefix apps/gui-web
```

UI 默认运行在 `http://127.0.0.1:5173`，并连接 `http://127.0.0.1:8000`。如需连接其他本地 API，设置 `VITE_DRA_API_BASE_URL`。

## Artifacts

运行输出目录：

```text
workspace/research_jobs/<job_id>/
```

稳定 artifact 名称包括 `report.md`、`report.html`、`report_bundle.json`、`sources.json`、`claims.json`、`audit_decision.json`、`review_queue.json`、`claim_graph.json`、`trace.jsonl` 和 `manifest.json`。

## 文档

- [用户指南](./docs/USER_GUIDE.md)
- [API](./docs/API.md)
- [Artifacts](./docs/ARTIFACTS.md)
- [架构](./docs/ARCHITECTURE.md)

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
