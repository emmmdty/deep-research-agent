# Phase 01: runtime / state / persistence / lease / event log 基础重构

## 0. 文档状态
- 当前状态：active
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-01-runtime-state-persistence`
- branch：`refactor/phase-01-runtime-state-persistence`
- 基线提交：`c8f5af2`
- 最近更新：`2026-04-20T13:30:00Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P0-1 worker lease/stale recovery 非并发安全；P0-2 event/checkpoint 序号非事务化且可覆盖；P1-4 缺少关键失败路径测试。
- 为什么现在先做这些：lease、event、checkpoint 是 public runtime 的底座；后续 cancel/retry/resume、audit artifact、API readiness 都依赖它们可信。
- 如果不先做会发生什么：同一 job 可能被多个 worker 推进，event/checkpoint 可被覆盖或乱序，报告与 audit sidecar 的执行轨迹不再可信。

## 2. 范围

### 2.1 改动目录
- `services/research_jobs/`
- `tests/test_phase2_jobs.py`
- `docs/architecture.md`
- `docs/refactor/phase-01-runtime-state-persistence.md`

### 2.2 改动边界
- 会改什么：SQLite store 的 job lease、heartbeat、event append、checkpoint save 语义；worker 获取 lease 的调用方式；orchestrator 写 event/checkpoint 的序号获取方式；相关测试与文档。
- 不会改什么：connector/policy/fetch security、claim audit 算法、HTTP/API server、legacy graph 产品边界、Postgres/object storage 迁移。

### 2.3 非目标
- 非目标 1：不引入外部队列、Celery、Redis、Postgres 或常驻 server。
- 非目标 2：不把当前本地 subprocess runtime 声称为多实例生产就绪。

## 3. 现状与问题
- 当前代码路径：`ResearchJobStore.attach_worker()` 直接覆盖 `worker_pid/worker_lease_id`；`heartbeat()` 只在 lease mismatch 时跳过心跳；`next_event_sequence()` 和 `next_checkpoint_sequence()` 使用 `MAX(sequence)+1`；`append_event()` 和 `save_checkpoint()` 使用 `INSERT OR REPLACE`。
- 当前行为：worker 启动即覆盖 lease 并进入 `service.run_job()`；stale recovery 根据 heartbeat/PID 推断后直接 spawn 新 worker；event/checkpoint 分配序号与写入分离。
- 当前缺陷：没有原子 lease acquire；没有 lease fencing；event/checkpoint 可静默 replace；序号分配不是事务的一部分；`ResearchJobService._append_event()` 对单个事件取号两次。
- 对产品化 / 可靠性 / 安全性的影响：执行轨迹可能失真，恢复可能导致双 worker，审计和 report bundle 无法证明单一执行历史。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：同一 active job 在任一时刻只能有一个有效 worker lease。
- 目标 2：event log 对单个 job append-only，sequence 单调，不允许静默覆盖。
- 目标 3：checkpoint metadata 与 payload 写入保持单调，不允许同一 sequence 被覆盖。

### 4.2 方案描述
- 关键设计：在 store 内增加原子 lease acquire 方法，只有无 lease 或调用方显式允许恢复 stale lease 时才能写入；orchestrator 每次推进阶段前检查当前 lease fence。
- 状态模型变化：保留现有 `worker_lease_id` 字段；本 phase 不新增长期公开字段，必要的内部错误通过异常和 event 表达。
- 存储 / 接口 / 契约变化：event/checkpoint 写入由 store 在同一事务中分配 sequence 并 insert；append API 不再依赖调用方预先生成 sequence。
- 对 legacy 的处理：不改 `workflows/graph.py`，不把 legacy `auditing` 路径提升为 public runtime。

### 4.3 权衡
- 为什么不用方案 A：不直接引入 Postgres/queue，因为本 phase 目标是把当前 SQLite 单机 runtime 做到可解释，不提前引入服务化复杂度。
- 为什么当前方案更合适：它能用现有依赖验证最危险的不变量，并为后续 Phase 2/6 迁移保留清晰边界。
- 代价是什么：SQLite 仍不是多实例生产存储；本 phase 只能证明单机/本地 worker 模型下的更强一致性。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase 分支中的 `services/research_jobs/`、`tests/`、`docs/` 修改。
- 回滚后仍保持什么能力：旧 CLI job happy path、cancel/retry、claim audit bundle 仍按 Phase 0 基线运行。
- 回滚会丢失什么：lease fencing、append-only event/checkpoint 和相关失败路径测试。

## 5. 实施清单
- [x] 写失败测试：第二个 worker 不能覆盖已有活跃 lease。
- [x] 写失败测试：lease mismatch 的 worker 不能推进阶段或清理别人的 lease。
- [x] 写失败测试：event append 不能覆盖同一 sequence，store 应自行分配单调 sequence。
- [x] 写失败测试：checkpoint save 不能覆盖同一 sequence，store 应自行分配单调 sequence。
- [x] 实现 store 原子 lease acquire / fenced heartbeat / fenced clear worker。
- [x] 实现 event/checkpoint 事务化 sequence 分配与 append-only insert。
- [x] 更新 service/worker/orchestrator 调用点。
- [x] 更新架构文档和本 phase 验证结果。

## 6. 实际修改

### 6.1 修改的文件
- `services/research_jobs/store.py`
- `services/research_jobs/service.py`
- `services/research_jobs/worker.py`
- `services/research_jobs/orchestrator.py`
- `tests/test_phase2_jobs.py`
- `docs/architecture.md`
- `docs/refactor/phase-01-runtime-state-persistence.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`services/research_jobs/store.py`
- 变更点：新增 `WorkerLeaseConflict`、`acquire_worker_lease()`、`assert_worker_lease()`，`clear_worker()` 支持 lease fencing；`append_event()` 和 `save_checkpoint()` 在事务中分配 sequence 并使用 `INSERT INTO`。
- 原因：防止活跃 worker lease 被覆盖，防止 event/checkpoint 静默覆盖。
- 文件：`services/research_jobs/worker.py`
- 变更点：worker 启动时 acquire lease，执行 job 时传入 `worker_lease_id`，退出时只清理自己的 lease。
- 原因：避免旧 worker 退出清理新 worker lease。
- 文件：`services/research_jobs/orchestrator.py`
- 变更点：支持可选 `worker_lease_id`，带 lease 运行时先做 fence check；event/checkpoint 使用 pending 占位交给 store 分配序号。
- 原因：lease mismatch worker 不应推进阶段或写轨迹。
- 文件：`services/research_jobs/service.py`
- 变更点：`run_job()` 传递 worker lease；stale recovery 先 fenced clear 旧 lease 再 spawn；初始 checkpoint 和 service event 使用 store 返回的真实 ID/sequence。
- 原因：恢复路径不再无条件覆盖 owner。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：不涉及 DB schema 迁移。
- 是否涉及 artifact 变化：不改变 report bundle wire shape；trace/event sequence 语义更严格。
- 是否影响 CLI / benchmark / comparator / legacy-run：影响 public CLI runtime 的 worker ownership 与 event/checkpoint 写入；不修改 `legacy-run`、benchmark、comparator 入口。

## 7. 验收标准

### 7.1 功能验收
- [x] `submit/status/watch/cancel/retry` parser 仍可用。
- [x] happy path job orchestrator 仍输出 report、bundle、trace。

### 7.2 失败路径验收
- [x] 已有活跃 lease 时，第二个 worker acquire 失败且不能覆盖 lease。
- [x] stale recovery 只 fenced clear 扫描时看到的旧 lease，新 worker 仍必须 acquire lease。
- [x] lease mismatch worker 不能推进阶段或 clear 当前 worker。
- [x] event/checkpoint 不允许静默覆盖既有 sequence。

### 7.3 回归验收
- [x] `uv run pytest -q tests/test_phase2_jobs.py`
- [x] `uv run pytest -q tests/test_phase4_auditor.py`

### 7.4 文档验收
- [x] `docs/architecture.md` 更新当前 runtime 的 lease/event/checkpoint 事实。
- [x] `docs/refactor/phase-01-runtime-state-persistence.md` 写入实际修改和验证结果。

### 7.5 不变量验收
- [x] 同一 active job 不能被两个有效 lease 同时推进。
- [x] event sequence 单调且 append-only。
- [x] checkpoint sequence 单调且不覆盖。

## 8. 验证结果

### 8.1 执行的命令
```bash
uv run pytest -q tests/test_phase2_jobs.py
uv run pytest -q tests/test_phase4_auditor.py
uv run python main.py --help
uv run ruff check services/research_jobs tests/test_phase2_jobs.py
uv run pytest -q
uv run ruff check .
```

### 8.2 结果
- 通过：基线 `tests/test_phase2_jobs.py`，`9 passed in 2.36s`。
- 通过：红绿后 `tests/test_phase2_jobs.py`，`15 passed in 1.51s`。
- 通过：`tests/test_phase4_auditor.py`，`7 passed in 1.04s`。
- 通过：`uv run python main.py --help` 正常输出 `submit/status/watch/cancel/retry`。
- 通过：`uv run ruff check services/research_jobs tests/test_phase2_jobs.py`，`All checks passed!`。
- 通过：`uv run pytest -q`，`155 passed in 5.38s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。非提权全量 pytest 曾因仓库外 worktree 不能写 `workspace/` 失败，最终使用提权验证通过。

### 8.3 证据
- 测试输出摘要：`9 passed in 2.36s`；`15 passed in 1.51s`；`7 passed in 1.04s`；`155 passed in 5.38s`；ruff 全量通过。
- 手工验证摘要：worktree 分支为 `refactor/phase-01-runtime-state-persistence`，起点为 `c8f5af2`。
- 仍存风险：SQLite 仍是单机存储；`upsert_job()` 仍保留 `INSERT OR REPLACE`，本 phase 只收敛 event/checkpoint append-only 和 worker lease/fencing。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`，保留 Phase 1 文档和单一实现提交。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板、`docs/architecture.md`。
- 需要同步的测试：Phase 2 可能复用新增 lease/event/checkpoint 不变量测试。
- 下一 phase 进入条件：Phase 1 合并回 main，runtime 基础不变量验收通过。

## 11. 复盘
- 本 phase 最大收益：public runtime 的 worker ownership 与执行轨迹写入不再依赖调用方自觉，关键不变量有测试保护。
- 新发现的问题：`upsert_job()` 仍使用 `INSERT OR REPLACE`，后续 Phase 2 应继续收敛 job row 更新的条件写入与 canonical state projection。
- 是否需要回写总计划：需要，Phase 1 验收后回写状态看板和实际结果。
