# Phase 06: API readiness 与 server surface 铺底

## 0. 文档状态
- 当前状态：accepted
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-06-api-readiness`
- branch：`refactor/phase-06-api-readiness`
- 基线提交：`b70ecbd`
- 最近更新：`2026-04-20T15:50:16Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P0 本地 CLI/subprocess/SQLite/path runtime 不是平台底座；P3 文档广度高于底层成熟度。
- 为什么现在先做这些：Phase 1-5 已加固 public runtime、security、audit 和 release gate；最后一步需要明确哪些合同可被未来 API 复用，哪些仍然不能写成当前能力。
- 如果不先做会发生什么：后续 server/UI 工作可能直接固化旧 CLI/path artifact 形态，或把 readiness 文档误写成已支持 HTTP/API。

## 2. 范围

### 2.1 改动目录
- `docs/adr/`
- `specs/`
- `tests/`
- `docs/refactor/phase-06-api-readiness.md`

### 2.2 改动边界
- 会改什么：新增 API readiness ADR、目标 contract 草案、回归测试，明确 job/artifact/auth/storage/queue 边界。
- 不会改什么：不新增 FastAPI/Flask/HTTP server，不新增 web UI，不改变 public CLI，不迁移 Postgres/queue/object storage。

### 2.3 非目标
- 非目标 1：不交付正式 HTTP API。
- 非目标 2：不承诺多租户、认证、队列、对象存储已实现。

## 3. 现状与问题
- 当前代码路径：公开 runtime 仍是 `main.py + services/research_jobs/`；artifact 在 `workspace/research_jobs/<job_id>/`；release gate 是本地 manifest。
- 当前行为：`main.py --help` 只暴露 `submit/status/watch/cancel/retry`；仓库没有 supported HTTP/API server surface。
- 当前缺陷：未来 API 的资源边界、可复用合同和必须新建的生产服务边界还缺少集中 ADR/spec。
- 对产品化 / 可靠性 / 安全性的影响：没有 readiness 文档时，server 可能过早复制本地路径、SQLite、subprocess worker 和单用户假设。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：ADR 明确当前无 supported HTTP/API surface，server 实现进入下一 release train。
- 目标 2：contract 草案列出未来 Job / Artifact / Audit / Source / Event API 的目标资源，不把它们写成当前实现。
- 目标 3：测试固定“不新增 server surface / 不引入 FastAPI/Uvicorn / docs 明确 readiness-only”。

### 4.2 方案描述
- 关键设计：新增 `adr-0007-api-readiness-boundary.md` 和 `specs/api-readiness-contract.md`，只描述边界和迁移前置条件。
- 状态模型变化：不改变 runtime state。
- 存储 / 接口 / 契约变化：不新增 runtime 接口；新增目标 API contract 文档。
- 对 legacy 的处理：legacy-run、benchmark/comparator 仍不作为未来 API 边界。

### 4.3 权衡
- 为什么不用方案 A：不直接实现 server，因为当前 storage/queue/auth/tenant/object storage 仍未产品化。
- 为什么当前方案更合适：把已加固的合同与未实现的能力分开，防止未来能力误写成当前事实。
- 代价是什么：Phase 6 的主要产物是 ADR/spec/tests，不提供新用户入口。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase ADR/spec/tests/docs。
- 回滚后仍保持什么能力：Phase 1-5 public runtime、audit、release gate 不受影响。
- 回滚会丢失什么：API readiness 边界文档和防止 server surface 误引入的测试。

## 5. 实施清单
- [x] 写失败测试：API readiness ADR/spec 必须存在并声明当前无 supported HTTP/API surface。
- [x] 写失败测试：仓库不得新增 server entrypoint。
- [x] 新增 API readiness ADR。
- [x] 新增目标 API contract 草案。
- [x] 更新 phase 文档和验证结果。

## 6. 实际修改

### 6.1 修改的文件
- `docs/adr/adr-0007-api-readiness-boundary.md`
- `specs/api-readiness-contract.md`
- `tests/test_phase6_api_readiness.py`
- `docs/architecture.md`
- `docs/refactor/phase-06-api-readiness.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`docs/adr/adr-0007-api-readiness-boundary.md`
- 变更点：记录当前无 supported HTTP/API server surface，server implementation 进入下一 release train。
- 原因：防止 API readiness 被误写成已实现 API。
- 文件：`specs/api-readiness-contract.md`
- 变更点：记录未来 Job / Artifact / Source / Audit resource contract 和实现前置 ADR。
- 原因：让后续 server/API 工作复用 public runtime 合同，而不是 legacy graph 或本地路径。
- 文件：`tests/test_phase6_api_readiness.py`
- 变更点：新增 readiness docs、no server entrypoint、CLI surface 回归。
- 原因：用测试固定 Phase 6 非目标。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：不涉及。
- 是否涉及 artifact 变化：不涉及。
- 是否影响 CLI / benchmark / comparator / legacy-run：不应影响。

## 7. 验收标准

### 7.1 功能验收
- [x] ADR/spec 说明未来 API 的 job/artifact/audit/source/event 边界。
- [x] ADR/spec 明确当前没有 supported HTTP/API server surface。

### 7.2 失败路径验收
- [x] 如果新增 server entrypoint 或服务依赖，测试失败。
- [x] 如果文档把 future API 写成当前能力，测试失败。

### 7.3 回归验收
- [x] `uv run python main.py --help`
- [x] `uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py`
- [x] `uv run pytest -q tests/test_phase6_api_readiness.py tests/test_public_repo_standards.py`
- [x] `uv run pytest -q`
- [x] `uv run ruff check .`

### 7.4 文档验收
- [x] ADR/spec 被更新。
- [x] phase 文档写入实际验证结果。

### 7.5 不变量验收
- [x] 不新增 HTTP/API server。
- [x] 不把 API readiness 写成已实现 API。
- [x] CLI-first public surface 保持不变。

## 8. 验证结果

### 8.1 执行的命令
```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv PYTHONDONTWRITEBYTECODE=1 uv run python main.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase6_api_readiness.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_phase6_api_readiness.py tests/test_public_repo_standards.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase06-venv uv run ruff check .
```

### 8.2 结果
- 通过：基线 `tests/test_phase2_jobs.py tests/test_phase4_auditor.py`，`29 passed in 2.45s`。
- 通过：基线 `main.py --help`，只暴露 `submit/status/watch/cancel/retry`。
- 通过：红灯 `tests/test_phase6_api_readiness.py`，`1 failed, 2 passed`。
- 通过：红绿后 `tests/test_phase6_api_readiness.py`，`3 passed in 0.46s`。
- 通过：fresh `main.py --help`，只暴露 `submit/status/watch/cancel/retry`。
- 通过：fresh `tests/test_phase2_jobs.py tests/test_phase4_auditor.py`，`29 passed in 2.44s`。
- 通过：`tests/test_phase6_api_readiness.py tests/test_public_repo_standards.py`，`12 passed in 2.56s`。
- 通过：`uv run pytest -q`，`170 passed in 7.76s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。

### 8.3 证据
- 测试输出摘要：基线 `29 passed in 2.45s`；红灯 `1 failed, 2 passed`；红绿 `3 passed in 0.46s`；public surface `12 passed in 2.56s`；全量 `170 passed in 7.76s`。
- 手工验证摘要：worktree 分支为 `refactor/phase-06-api-readiness`，起点为 `b70ecbd`。
- 仍存风险：API readiness 只给出 contract 草案，不交付 server。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板。
- 需要同步的测试：后续 server 实现必须先更新 ADR/spec，再移除或调整 no-server-surface 测试。
- 下一 phase 进入条件：本轮重构计划结束；server implementation 进入下一 release train。

## 11. 复盘
- 本 phase 最大收益：API readiness 被固定为 ADR/spec/test 合同，没有新增半成品 server surface。
- 新发现的问题：后续 server implementation 仍需要 auth、tenant、storage、queue、artifact storage、rate limit 和 audit log ADR。
- 是否需要回写总计划：需要，Phase 6 合并后回写状态看板和实际结果。
