# Deep Research Agent

[![CI](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/emmmdty/deep-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[English](./README.md) | 简体中文

面向公司/行业研究的 evidence-first Deep Research Agent。当前仓库的主线不是聊天壳，也不是“多 agent 数量展示”，而是一个本地可运行、可恢复、可审计的研究 job runtime；当前 `main` 还提供了叠加在本地 API 之上的 operator/reviewer Web GUI 与有边界的 Tauri desktop wrapper。

## 从哪里开始

- 先看 [仓库地图](./docs/REPO_MAP.md)：了解哪些根目录是 canonical、compatibility、benchmark/eval、legacy/archive。
- 再看 [文档索引](./docs/DOCS_INDEX.md)：按 reviewer 视角阅读最终文档。
- 看 `src/deep_research_agent/`：当前 canonical 实现。
- 看 `evals/reports/phase5_local_smoke/`：权威 merge-safe `smoke_local` gate。
- 看 [Native Benchmark](./docs/benchmarks/native/README.md)：确定性的 `regression_local` reviewer evidence。
- 看 [GUI 文档](./docs/gui/README.md)：本地 operator/reviewer GUI 与 desktop 状态。

## 当前项目边界

当前公开支持的能力包括：

- 确定性异步 job runtime
- source policy + snapshotting
- claim-level audit + review queue
- report bundle 交付物
- OpenAI / Anthropic / compatible provider abstraction
- CLI、本地 HTTP API、本地 Web GUI、bounded Tauri desktop wrapper、batch entrypoint
- 本地 eval runner、`smoke_local` release gate、`regression_local` native regression layer

本地 HTTP API 是真实实现，但仍然基于 SQLite、filesystem artifacts 和本地 worker。它不是带 auth、tenant isolation、外部 queue、object storage 的生产 SaaS 边界。

## 主要入口

### CLI

支持的 developer CLI 通过 `main.py` 暴露：

- `submit`
- `status`
- `watch`
- `cancel`
- `retry`
- `resume`
- `refine`
- `bundle`
- `batch run`
- `eval run`
- `benchmark run`

### 本地 HTTP API

本地 FastAPI surface 复用同一套 deterministic job runtime：

- `POST /v1/research/jobs`
- `GET /v1/research/jobs/{job_id}`
- `GET /v1/research/jobs/{job_id}/events`
- `POST /v1/research/jobs/{job_id}:cancel`
- `POST /v1/research/jobs/{job_id}:retry`
- `POST /v1/research/jobs/{job_id}:resume`
- `POST /v1/research/jobs/{job_id}:refine`
- `POST /v1/research/jobs/{job_id}:review`
- `GET /v1/research/jobs/{job_id}/bundle`
- `GET /v1/research/jobs/{job_id}/artifacts/{artifact_name}`
- `POST /v1/batch/research`

### 本地 Web GUI 与 Desktop

- Web GUI 位于 `apps/gui-web/`，默认请求本地 API `http://127.0.0.1:8000`
- Tauri desktop wrapper 位于 `desktop/tauri/`
- GUI/desktop 只是当前 runtime 的 operator/reviewer surface，不把 runtime、provider、audit、benchmark 逻辑搬进前端或 Rust

启动 Web GUI：

```bash
cd apps/gui-web
npm install
npm run dev
```

有边界的 desktop 自检：

```bash
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri
```

## 快速开始

### 1. 安装依赖

```bash
uv sync --group dev
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

运行 live research 前需要补齐 provider 和 search credentials。

### 3. 提交并查看研究任务

```bash
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --allow-domain anthropic.com \
  --max-candidates-per-connector 4 \
  --max-fetches-per-task 3 \
  --max-total-fetches 8

uv run python main.py watch --job-id <job_id>
uv run python main.py status --job-id <job_id>
uv run python main.py bundle --job-id <job_id> --json
```

### 4. 启动本地 HTTP API

```bash
uv run uvicorn deep_research_agent.gateway.api:app --reload
```

提交并检查一个本地 job：

```bash
curl -s http://127.0.0.1:8000/v1/research/jobs \
  -X POST \
  -H 'content-type: application/json' \
  -d '{
    "topic": "AI coding agent market map",
    "max_loops": 2,
    "research_profile": "default",
    "source_profile": "industry_broad",
    "start_worker": false
  }'

curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/events
curl -s http://127.0.0.1:8000/v1/research/jobs/<job_id>/bundle
```

### 5. 运行 batch

创建 `batch.jsonl`：

```jsonl
{"topic":"Anthropic company profile","max_loops":1,"research_profile":"default","start_worker":false}
{"topic":"AI coding agent market map","max_loops":2,"research_profile":"benchmark","source_profile":"industry_broad","start_worker":false}
```

提交：

```bash
uv run python main.py batch run --file batch.jsonl --json
```

### 6. 运行本地 eval、release smoke 和 native regression

```bash
uv run python main.py eval run --suite company12 --output-root evals/reports/phase5_local_smoke/company12 --json
uv run python main.py eval run --suite industry12 --output-root evals/reports/phase5_local_smoke/industry12 --json
uv run python main.py eval run --suite company12 --variant regression_local --output-root evals/reports/native_regression/company12 --json
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke --json
uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression --json
uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native --json
```

解释：

- `smoke_local` 是权威 merge-safe gate，提交产物位于 `evals/reports/phase5_local_smoke/`。
- `regression_local` 是更宽的 deterministic native regression layer，提交产物位于 `evals/reports/native_regression/`。
- reviewer-facing native docs 位于 `docs/benchmarks/native/`。

## Artifact Contract

完成态 job 会写入 `workspace/research_jobs/<job_id>/`。

稳定 artifact 名称：

- `report.md`
- `report.html`
- `report_bundle.json`
- `claims.json`
- `sources.json`
- `audit_decision.json`
- `trace.jsonl`
- `manifest.json`
- `review_queue.json`
- `claim_graph.json`
- `review_actions.jsonl`

`report_bundle.json` 是权威机器可读输出；其他文件是阅读、审计和交付视图。

## Source Profiles

当前 canonical source profile 包括：

- `company_trusted`
- `company_broad`
- `industry_trusted`
- `industry_broad`
- `public_then_private`
- `trusted_only`

## 仓库结构

当前 canonical execution path 位于 `src/deep_research_agent/`：

```text
src/deep_research_agent/
  gateway/          CLI、本地 HTTP API、batch helpers、public contracts
  research_jobs/    deterministic runtime、store、service、worker、orchestrator
  connectors/       search / fetch / file-ingest substrate 与 snapshot store
  auditor/          claim audit、review queue、audit sidecars
  reporting/        bundle compiler 与 delivery artifacts
  providers/        provider routing 与 abstraction
  evidence_store/   evidence storage primitives
  evals/            deterministic local suite runner 与 eval contracts
evals/              suite definitions、frozen datasets、rubrics、committed smoke/regression outputs
docs/               architecture、development、final docs、benchmark docs、migration notes
legacy/             archived graph/runtime material and compatibility-only references
tests/              runtime、connector、auditor、public-surface、benchmark regressions
```

根目录下的 `artifacts/`、`auditor/`、`connectors/`、`services/`、`llm/`、`memory/`、`tools/` 等目录主要是 compatibility/support path，不是主架构入口。完整分类见 [仓库地图](./docs/REPO_MAP.md)。

## 开发与验证

关键本地检查：

```bash
uv run python main.py --help
uv run ruff check .
uv run pytest -q tests/test_cli_runtime.py tests/test_phase4_surfaces.py
uv run python scripts/run_local_release_smoke.py --output-root evals/reports/phase5_local_smoke
uv run python scripts/run_native_regression.py --output-root evals/reports/native_regression
uv run python scripts/build_native_benchmark_summary.py --reports-root evals/reports/native_regression --docs-root docs/benchmarks/native
```

相关文档：

- [仓库地图](./docs/REPO_MAP.md)
- [文档索引](./docs/DOCS_INDEX.md)
- [架构设计](./docs/architecture.md)
- [开发指南](./docs/development.md)
- [最终变更报告](./FINAL_CHANGE_REPORT.md)
- [实验总结](./docs/final/EXPERIMENT_SUMMARY.md)
- [Native Scorecard](./docs/benchmarks/native/NATIVE_SCORECARD.md)
- [Native Casebook](./docs/benchmarks/native/CASEBOOK.md)
- [Native 中文使用手册](./docs/benchmarks/native/USAGE_GUIDE.zh-CN.md)
- [GUI 文档](./docs/gui/README.md)
- [Desktop 状态](./docs/gui/DESKTOP_STATUS.md)

## 当前限制

- 本地 HTTP API 仍使用 SQLite、filesystem artifacts 和本地 subprocess worker。
- 当前没有 auth、tenant isolation、external queue 或 object storage layer。
- manual review 是 append-only 并可通过 events/sidecars 观察，但不会完整重编译 `report_bundle.json`。
- `legacy-run` 仍作为 hidden compatibility path 存在，不是 supported public runtime。
- heavy benchmark/comparator stack 仍可用于 diagnostics，但权威 release gate 是 `evals/reports/phase5_local_smoke/`。
- external benchmark portfolio 是 smoke/subset-first reviewer-facing diagnostics，不是 production benchmark service。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
