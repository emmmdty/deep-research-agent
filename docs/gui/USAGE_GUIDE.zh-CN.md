# GUI 使用指南

这个 GUI 是 Deep Research Agent 的本地 operator/reviewer 控制台。它覆盖已有的本地 FastAPI、报告 bundle、artifact、审计状态和 native benchmark 证据；它不是聊天壳，也不是多租户 SaaS 控制台。

## 1. 启动后端 API

在仓库根目录执行：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run uvicorn deep_research_agent.gateway.api:app --host 127.0.0.1 --port 8000
```

默认 GUI API 地址是：

```text
http://127.0.0.1:8000
```

## 2. 启动 Web GUI

```bash
cd apps/gui-web
npm install
npm run dev
```

打开 Vite 输出的本地地址。

## 3. 提交本地 bounded job

1. 在 `New local research job` 中输入 topic，例如 `Anthropic company profile`。
2. 选择 source profile，例如 `company_trusted`。
3. 点击 `Submit local job`。
4. GUI 会用 `start_worker=false` 调用 `POST /v1/research/jobs`，用于验证 API 合同但不会启动长时间 worker。
5. 返回的 job id 会进入浏览器本地的 Known Jobs 列表。

## 4. 查看已有 job

1. 在 `Manual job id` 输入 job id。
2. 点击 `Load job`。
3. 查看 `Status`、`Audit gate`、`Stage`、`Blocked critical claims`。
4. 事件来自 `/v1/research/jobs/{job_id}/events?after_sequence=0`。
5. 点击 `Load bundle` 查看原始 `report_bundle.json`。

## 5. 查看 benchmark console

Benchmark console 展示仓库已提交的 deterministic native benchmark 证据：

- `smoke_local`: 权威 merge-safe gate。
- `regression_local`: reviewer-facing 回归覆盖层。
- suites: `company12`、`industry12`、`trusted8`、`file8`、`recovery6`。
- links: Native scorecard、casebook、smoke manifest、regression manifest。

GUI 不会从浏览器启动长跑 benchmark，也不会引入外部 benchmark 集成。

## 6. Desktop 状态

当前 desktop 状态是 `READY_FOR_TAURI_BUILD`。

已验证：

- Rust/Cargo、Node/npm、WebKitGTK 4.1 等 Tauri Linux 前置条件可用。
- `apps/desktop-tauri/` 已包含 Tauri 2 wrapper。
- `tauri info`、bounded dev wiring、`tauri build --no-bundle` 均已通过。

如果用户级 npm/Cargo cache 目录只读，请使用 `npm_config_cache=/tmp/npm-cache` 和 `CARGO_HOME=/tmp/cargo-home`。

## 7. 本地验证

```bash
cd apps/gui-web
npm test
npm run lint
npm run build
```

Desktop 验证：

```bash
npm_config_cache=/tmp/npm-cache npm install --prefix apps/desktop-tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix apps/desktop-tauri
```

后端 smoke：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_phase4_surfaces.py::test_http_api_submit_status_events_bundle_and_artifacts
```
