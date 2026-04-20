# 交付摘要

- 生成时间：`2026-04-20T16:12:53Z`
- Phase 7 基线：`main@cf8b0a8`
- 交付状态：Phase 0-6 已完成并通过 Phase 7 最终验收。

## 1. 本轮变更摘要

本轮把仓库从 CLI-first 研究原型推进为更可解释的可信研究 runtime 原型：

- Runtime：同一 active job 不能被两个有效 lease 同时推进；event/checkpoint sequence 单调、append-only。
- Orchestration：cancel/retry/recovery 行为更可预测。
- Connector security：public fetch 前阻止明显不安全 URL。
- Audit：claim support edge 携带 grounding metadata；critical claim 缺 grounded evidence 时 blocked。
- Release：新增本地 release gate manifest，benchmark diagnostics 不能单独代表发布。
- API readiness：新增 ADR/spec，明确当前没有受支持的 HTTP/API server surface。

## 2. 关键文件

- `docs/refactor/000-overall-transformation-plan.md`：总计划与 Phase 0-6 状态看板。
- `docs/refactor/phase-01-runtime-state-persistence.md` 到 `docs/refactor/phase-06-api-readiness.md`：各阶段范围、风险、验收和实际结果。
- `services/research_jobs/`：public runtime 主干。
- `connectors/`、`policies/`：connector/policy/fetch security 边界。
- `auditor/`、`schemas/claim-support.schema.json`、`schemas/report-bundle.schema.json`：claim audit grounding。
- `configs/release_gate.yaml`、`scripts/release_gate.py`：本地 release gate。
- `docs/adr/adr-0007-api-readiness-boundary.md`、`specs/api-readiness-contract.md`：API readiness 边界。

## 3. 关键不变量变化

- 同一 active job 只能由一个有效 worker lease 推进。
- worker 只有持有匹配 lease 才能清理自身 lease 或继续写入关键状态。
- event/checkpoint 由 store 在写入事务中分配 sequence，不允许静默覆盖。
- cancel/retry 是可预测幂等语义。
- fetch 前会执行 URL safety check；明显本机/私网/非 HTTP(S) URL 会被拦截。
- critical claim 必须有 grounded non-context evidence edge 才能通过，否则进入 review queue。
- benchmark diagnostics 是必需诊断信号，但不能单独让 release gate 通过。
- API readiness 只存在于 ADR/spec，不是当前已实现 API。

## 4. 测试与验证摘要

Phase 7 最终验收命令与结果：

- `uv run python main.py --help`：通过，只暴露 `submit/status/watch/cancel/retry`。
- `uv run python scripts/run_benchmark.py --help`：通过。
- `uv run python scripts/full_comparison.py --help`：通过。
- 关键定向测试：`59 passed in 5.40s`。
- 全量测试：`170 passed in 7.61s`。
- 全量 ruff：`All checks passed!`。

## 5. CLI / Public Surface 最终说明

当前公开入口仍然只有：

```text
submit / status / watch / cancel / retry
```

`legacy-run` 仍是 hidden compatibility path。`workflows/graph.py` 仍是 legacy runtime，不是未来产品顶层边界。当前没有 supported HTTP/API server surface。

## 6. Web/API Readiness 最终说明

Phase 6 已完成 API readiness 文档和测试：

- `docs/adr/adr-0007-api-readiness-boundary.md`
- `specs/api-readiness-contract.md`
- `tests/test_phase6_api_readiness.py`

这些文件只描述目标契约和前置条件，不代表当前已实现 server。后续 server implementation 必须先补 auth/tenant/storage/queue/object storage/rate limit/audit log ADR，并进入新的 release train。

## 7. 仍未解决的问题

- 企业级 server/API/auth/tenant 未实现。
- 生产级 storage/object storage/queue 未实现。
- DNS/redirect 级 SSRF 防护和集中 fetch proxy 未实现。
- claim audit 仍不是完整自动事实验证。
- release gate 仍不是 CI/CD 或生产监控系统。
