# 最终验收报告

- 生成时间：`2026-04-20T16:12:53Z`
- 验收分支：`refactor/phase-07-finalize`
- 基线 main：`cf8b0a8`
- 结论：Phase 0-6 重构成果已完成最终一致性核对；当前仍不是企业产品级深度研究工具。

## 1. 本轮范围

本轮覆盖 `docs/refactor/000-overall-transformation-plan.md` 中的 Phase 0-6：

- Phase 0：恢复 Git 历史、提交重构输入文件、落地总计划。
- Phase 1：加固 job runtime 的 worker lease、event、checkpoint、SQLite 写入语义。
- Phase 2：收敛 cancel / retry / stale recovery / checkpoint projection 语义。
- Phase 3：加固 connector fetch 前 URL safety 与 source policy 边界。
- Phase 4：为 claim support edge 增加 grounding metadata，缺少 grounded evidence 的 critical claim 会 blocked。
- Phase 5：新增本地 release gate manifest，benchmark diagnostics 不能单独代表发布。
- Phase 6：新增 API readiness ADR/spec，明确当前没有受支持的 HTTP/API server surface。
- Phase 7：最终验收、交付文档收口、push/cleanup 清单。

非范围：

- 不交付 HTTP/API server。
- 不交付 web UI。
- 不迁移 Postgres / object storage / external queue。
- 不把启发式 audit 写成完整自动事实验证。

## 2. 已完成 Phases

| Phase | main 上提交 | 结果 |
|---|---:|---|
| Phase 0 | `c4e6d4d`, `c8f5af2` | 输入文件和总计划已提交 |
| Phase 1 | `8884453`, merge `296a7ca` | runtime lease/event/checkpoint 基础加固 |
| Phase 2 | `18fffb3`, merge `58fd585` | cancel/retry/recovery 语义收敛 |
| Phase 3 | `9ca45ba`, merge `59577d2` | connector fetch security 加固 |
| Phase 4 | `e0fef2b`, merge `6b85669` | claim audit grounding 加固 |
| Phase 5 | `f4b6987`, merge `c2d033a` | release gate manifest 落地 |
| Phase 6 | `40abaa3`, merge `9b9cb32` | API readiness ADR/spec 落地 |
| 总计划收尾 | `cf8b0a8` | Phase 0-6 状态为 completed |

## 3. 审计意见闭环情况

### P0

- worker lease / stale recovery 非并发安全：Phase 1 已加入 lease acquire/fencing、匹配 lease 才能清理 worker、失去 lease 后不能继续写 checkpoint/completed event。
- event/checkpoint 序号非事务化且可 replace：Phase 1 已改为 store 事务分配单调 sequence，append-only，不再由调用方预取号。
- 双状态源和恢复语义风险：Phase 2 收敛 cancel/retry 幂等和 stale recovery active lease 保护；双状态源仍是长期架构债。
- 本地 CLI/subprocess/SQLite/path runtime 不是平台底座：Phase 6 已明确 API readiness 只是目标契约，server 实现进入下一 release train。

### P1

- allow/deny domain 不是 fetch 安全边界：Phase 3 已增加非 http(s)、localhost、loopback/private/link-local 等显式 URL 拦截；DNS/redirect 级 SSRF 防护仍未完成。
- claim audit 是启发式 overlap：Phase 4 已让 edge 暴露 `source_id/snapshot_id/locator/grounding_status`，critical claim 没有 grounded edge 时 blocked；语义级事实核验仍未完成。
- legacy/new runtime 混杂：文档和 tests 固定 public runtime 为 `main.py + services/research_jobs/`，legacy graph 仍只作为 benchmark/comparator/hidden `legacy-run` 路径。
- 失败路径测试不足：Phase 1-6 已增加 lease、recovery、fetch security、audit grounding、release gate、API readiness 失败路径测试。

### P2 / P3

- benchmark / LLM judge 不能作为发布证明：Phase 5 release gate 已要求 runtime/security/audit/docs gate，benchmark diagnostics 不能单独通过。
- connector substrate 仍偏薄：Phase 3 仅加固 public fetch 前边界；平台级 connector/index/permission 仍未完成。
- SQLite / subprocess / local filesystem 仍偏本地原型：已在 Phase 6 ADR/spec 中明确为下一轮 server implementation 的前置阻塞。

## 4. 当前代码现实

- 当前真正支持的公开入口仍只有 CLI：`submit/status/watch/cancel/retry`。
- 当前公开 runtime：`main.py + services/research_jobs/`。
- 当前 legacy runtime：`workflows/graph.py`、hidden `legacy-run`、benchmark/comparator 相关路径。
- 当前没有受支持的 HTTP/API server surface。
- `release_gate` 是本地 manifest/checklist，不是外部 CI 或生产监控。
- `audit_gate_status=passed` 不等于完整自动事实验证；Phase 4 只是让 critical claim 必须有 grounded evidence edge 或进入 review queue。

## 5. 最终验证

在 `../dra-phase-07-finalize` 中执行：

```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv PYTHONDONTWRITEBYTECODE=1 uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_benchmark.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv PYTHONDONTWRITEBYTECODE=1 uv run python scripts/full_comparison.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase2_jobs.py tests/test_phase3_connectors.py tests/test_phase4_auditor.py tests/test_phase6_api_readiness.py tests/test_public_repo_standards.py tests/test_release_gate.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase07-venv uv run ruff check .
```

结果：

- `main.py --help`：只暴露 `{submit,status,watch,cancel,retry}`。
- `scripts/run_benchmark.py --help`：通过。
- `scripts/full_comparison.py --help`：通过。
- 关键定向测试：`59 passed in 5.40s`。
- 全量测试：`170 passed in 7.61s`。
- 全量 ruff：`All checks passed!`。

## 6. 尚未解决的问题

- 仍未迁移到服务型 runtime：auth、tenant、external queue、worker pool、Postgres、object storage、artifact service 均未实现。
- Fetch security 仍没有 DNS 解析、redirect 复检、集中 fetch proxy、内容大小/content-type 强制治理。
- Claim audit 仍使用启发式 relation classification，不是语义级事实核验。
- CLI 是开发/调试入口，不是长期产品契约。
- release gate 仍是本地 manifest，不是 CI/CD 或生产监控。

## 7. 是否达到企业产品级深度研究工具标准

没有达到。

当前已经从本地研究原型推进到“可解释、可测试、CLI-first 的可信研究 runtime 原型”。但企业产品级还缺少：

1. server/API/auth/tenant 基座；
2. 生产持久层和对象存储；
3. 外部队列与多 worker 调度；
4. 集中 outbound fetch security；
5. 语义级 claim verification 和人工复核工作流；
6. CI/CD release gate、observability、monitoring、SLO。

## 8. 下一轮建议优先级

1. **Server/runtime substrate**：先补 auth/tenant/storage/queue/object storage/rate limit/audit log ADR，再实现 API server。
2. **Security and connector platform**：集中 fetch proxy、DNS/redirect SSRF 防护、connector permission/index/snapshot versioning。
3. **Audit correctness**：span-grounded citation alignment、entity normalization、conflict adjudication、人工 review queue。
