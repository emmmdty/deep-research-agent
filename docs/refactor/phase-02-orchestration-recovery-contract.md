# Phase 02: job orchestration、恢复语义、取消/重试/幂等、artifact 契约收敛

## 0. 文档状态
- 当前状态：active
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-02-orchestration-recovery-contract`
- branch：`refactor/phase-02-orchestration-recovery-contract`
- 基线提交：`5b85a6a`
- 最近更新：`2026-04-20T13:56:00Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P0-3 `JobRuntimeRecord` 与 checkpoint `ResearchState` 的状态投影不够明确；P1-3 public/legacy stage vocabulary 漂移；P1-4 cancel/retry/recovery 缺少失败路径测试。
- 为什么现在先做这些：Phase 1 已加固 lease/event/checkpoint 写入；下一步必须让 job row、active checkpoint、cancel/retry/recovery 对外行为可预测。
- 如果不先做会发生什么：CLI status/watch、后续 API/UI、retry 派生、stale recovery 会继续读到不一致或重复的 runtime 事实。

## 2. 范围

### 2.1 改动目录
- `services/research_jobs/`
- `tests/test_phase2_jobs.py`
- `docs/architecture.md`
- `docs/refactor/phase-02-orchestration-recovery-contract.md`

### 2.2 改动边界
- 会改什么：cancel 幂等、retry 幂等、stale recovery 可测试语义、public status vocabulary 文档化、job row 与 active checkpoint 的投影测试。
- 不会改什么：不改 connector/security，不改 claim audit 算法，不引入 HTTP/API，不迁移 Postgres，不重写 legacy graph。

### 2.3 非目标
- 非目标 1：不把当前 CLI runtime 声称为 server-ready。
- 非目标 2：不删除 hidden `legacy-run` 或 benchmark/comparator legacy 依赖。

## 3. 现状与问题
- 当前代码路径：`ResearchJobService.cancel()` 每次调用都会追加 cancel event；`retry()` 每次调用都会创建新 job；`recover_stale_jobs()` 缺少针对活跃/陈旧 worker 的回归测试；public status vocabulary 仍需文档收敛。
- 当前行为：cancel/retry 是可用的，但重复调用会制造重复事件或重复 retry job。
- 当前缺陷：CLI/API 用户重复提交同一操作时缺少幂等边界；status 与 active checkpoint 的一致性缺少测试保护。
- 对产品化 / 可靠性 / 安全性的影响：后续 web/API 若直接复用，会产生重复 retry、重复 cancel event 和难解释的用户状态。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：重复 cancel 同一 job 不重复追加 cancel event，terminal job cancel 保持只读返回。
- 目标 2：重复 retry 同一 failed/cancelled/needs_review job 返回已有 retry job，不重复派生。
- 目标 3：stale recovery 的活跃/陈旧 worker 分支有测试保护，job row 与 active checkpoint projection 可解释。

### 4.2 方案描述
- 关键设计：在 store 增加按 `retry_of` 查询最新 retry 的只读方法；service 层做 cancel/retry 幂等判断；recovery tests 通过注入 `_process_exists` 和 `spawn_worker_fn` 验证分支。
- 状态模型变化：不新增 schema 字段；收敛文档和测试中的 public stage vocabulary。
- 存储 / 接口 / 契约变化：retry 对同一原 job 变成 idempotent create-or-return；cancel 对已请求/终态 job 变成 idempotent no-op。
- 对 legacy 的处理：保留 `auditing` 兼容分支，但不把它写成 public runtime 新 job 路径。

### 4.3 权衡
- 为什么不用方案 A：不在本 phase 引入 operation idempotency key 表，避免把 API/server 设计提前落进 CLI runtime。
- 为什么当前方案更合适：能解决当前 CLI 重复操作的真实风险，并为后续 API idempotency key 留出边界。
- 代价是什么：retry 幂等粒度是“原 job 只派生一个直接 retry”；如果需要再次重试，应对 retry job 本身调用 retry。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase 对 `services/research_jobs/`、`tests/`、`docs/` 的修改。
- 回滚后仍保持什么能力：Phase 1 的 lease/event/checkpoint 加固仍保留，除非回滚 merge 包含 Phase 1。
- 回滚会丢失什么：cancel/retry 幂等、recovery 分支测试和投影一致性测试。

## 5. 实施清单
- [x] 写失败测试：重复 cancel 不重复写 `job.cancel_requested` event。
- [x] 写失败测试：terminal job cancel 不改变 terminal status。
- [x] 写失败测试：重复 retry 同一原 job 返回同一 retry job。
- [x] 写失败测试：active heartbeat + live pid 不触发 stale recovery spawn。
- [x] 写失败测试：stale job 清理旧 lease 后触发 spawn，且保留 active checkpoint。
- [x] 写投影测试：active checkpoint `next_stage` 与 job row terminal/current_stage 可解释。
- [x] 实现 cancel/retry 幂等和 store retry 查询。
- [x] 更新架构文档和本 phase 验证结果。

## 6. 实际修改

### 6.1 修改的文件
- `services/research_jobs/store.py`
- `services/research_jobs/service.py`
- `tests/test_phase2_jobs.py`
- `docs/architecture.md`
- `docs/refactor/phase-02-orchestration-recovery-contract.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`services/research_jobs/store.py`
- 变更点：新增 `get_latest_retry(retry_of)`，按 `retry_of` 查询最新直接 retry job。
- 原因：让 service 层可以实现 retry create-or-return 语义。
- 文件：`services/research_jobs/service.py`
- 变更点：`cancel()` 对终态或已请求取消 job 直接返回；`retry()` 对同一原 job 若已有直接 retry 则返回既有 job。
- 原因：避免重复 cancel event 和重复 retry 派生。
- 文件：`tests/test_phase2_jobs.py`
- 变更点：新增 cancel/retry 幂等、stale recovery 活跃/陈旧分支、completed job active checkpoint projection 测试。
- 原因：补足 Phase 2 失败路径与投影一致性保护。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：预期不涉及。
- 是否涉及 artifact 变化：预期不改变 report bundle wire shape。
- 是否影响 CLI / benchmark / comparator / legacy-run：影响 CLI cancel/retry 的重复调用语义；不影响 legacy-run。

## 7. 验收标准

### 7.1 功能验收
- [x] happy path job orchestrator 仍输出 report/bundle/trace。
- [x] retry 仍能从 failed/cancelled/needs_review job 派生。

### 7.2 失败路径验收
- [x] 重复 cancel 不重复写事件。
- [x] terminal job cancel 不改 terminal status。
- [x] 重复 retry 不重复创建直接 retry job。
- [x] active worker 不被 stale recovery 误恢复。
- [x] stale worker 会触发恢复并清理旧 lease。

### 7.3 回归验收
- [x] `uv run pytest -q tests/test_phase2_jobs.py`
- [x] `uv run pytest -q tests/test_phase4_auditor.py`
- [x] `uv run pytest -q`

### 7.4 文档验收
- [x] `docs/architecture.md` 更新 cancel/retry/recovery 当前事实。
- [x] `docs/refactor/phase-02-orchestration-recovery-contract.md` 写入实际修改和验证结果。

### 7.5 不变量验收
- [x] retry_of 对同一直接原 job 不产生多个直接 retry。
- [x] cancel_requested event 对重复 cancel 保持单一语义。
- [x] active checkpoint 与 job row status/current_stage 可解释。

## 8. 验证结果

### 8.1 执行的命令
```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase02-venv uv run pytest -q tests/test_phase2_jobs.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase02-venv uv run pytest -q tests/test_phase4_auditor.py
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase02-venv uv run ruff check services/research_jobs tests/test_phase2_jobs.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase02-venv uv run python main.py --help
uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase02-venv uv run ruff check .
```

### 8.2 结果
- 通过：基线 `tests/test_phase2_jobs.py`，`15 passed in 1.81s`。
- 通过：红绿后 `tests/test_phase2_jobs.py`，`21 passed in 1.64s`。
- 通过：`tests/test_phase4_auditor.py`，`7 passed in 0.97s`。
- 通过：`uv run python main.py --help` 正常输出 `submit/status/watch/cancel/retry`。
- 通过：`uv run ruff check services/research_jobs tests/test_phase2_jobs.py`，`All checks passed!`。
- 通过：`uv run pytest -q`，`161 passed in 6.34s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。非提权 pytest 命令因仓库外 worktree 不能写 `.pytest_cache` 产生 warning；全量 pytest 使用提权验证通过。

### 8.3 证据
- 测试输出摘要：`15 passed in 1.81s`；`21 passed in 1.64s`；`7 passed in 0.97s`；`161 passed in 6.34s`；ruff 全量通过。
- 手工验证摘要：worktree 分支为 `refactor/phase-02-orchestration-recovery-contract`，起点为 `5b85a6a`。
- 仍存风险：本 phase 未引入 API 级 idempotency key；后续 Phase 6 需要定义 HTTP/API 层幂等策略。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`，保留 Phase 2 文档和实现提交。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板、`docs/architecture.md`。
- 需要同步的测试：Phase 3 应继续复用 recovery/cancel/retry 不变量。
- 下一 phase 进入条件：Phase 2 合并回 main，orchestration/recovery contract 验收通过。

## 11. 复盘
- 本 phase 最大收益：重复用户操作不再制造重复 runtime 事实，恢复分支和 terminal projection 有测试保护。
- 新发现的问题：CLI 层尚无用户可见的“已存在 retry job”说明；后续 API readiness 需要显式 response contract。
- 是否需要回写总计划：需要，Phase 2 验收后回写状态看板和实际结果。
