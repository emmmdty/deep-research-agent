# ADR-0005: Phase 02 使用 subprocess worker + SQLite job store + checkpoint files

- Status: Accepted
- Date: 2026-04-09

## Context

phase2 需要把一次性本地执行改成可恢复、可取消、可查询状态的 job runtime，同时保持仓库依旧轻量，不引入额外队列、外部数据库或 HTTP 服务。

## Decision

- 公开 CLI 采用 `submit / status / watch / cancel / retry`
- 每个 job 由独立 Python subprocess worker 执行
- runtime 状态、event、checkpoint metadata 存 `workspace/research_jobs/jobs.db`
- checkpoint payload 以 JSON 文件形式落在 `workspace/research_jobs/<job_id>/checkpoints/`
- legacy graph 继续保留，但只服务 benchmark、comparator 与 hidden `legacy-run`

## Consequences

- 当前仓库即可具备跨进程恢复、取消、重试和 stale job recovery 的基础能力
- phase2 不需要引入 Redis、Celery、Postgres 或额外守护进程
- public CLI 已不再直接持有研究主循环，但 benchmark/comparator 暂时仍不迁移

## Rejected Alternatives

### 单进程伪异步轮询

拒绝原因：

- 不能提供稳定的跨进程恢复语义
- cancel / stale recovery 边界不清晰

### 外部队列 / 常驻 worker 集群

拒绝原因：

- 超出 phase2 最小边界
- 会把工程复杂度提前抬高到 phase3/phase4 之后
