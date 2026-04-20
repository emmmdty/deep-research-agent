# ADR-0007: API readiness boundary without supported server surface

- Status: Accepted
- Date: 2026-04-20

## Context

Phase 1-5 已经收敛了 public runtime 的 job lifecycle、lease/event/checkpoint、connector security、claim audit grounding 和本地 release gate。下一步可以为未来 server/API 做契约准备，但当前仓库仍是 CLI-first public runtime。

当前没有受支持的 HTTP/API server surface。本文是目标契约，不是当前实现。

## Decision

- 当前公开入口仍是 `main.py submit/status/watch/cancel/retry`。
- Phase 06 只记录 API readiness 边界，不新增 server entrypoint、路由、监听端口或 web UI。
- 未来 API 必须复用已经稳定的 job-oriented 语义，而不是直接暴露 legacy graph。
- 未来 API 不得把本地 path artifact 当作长期外部契约；需要 artifact service 负责 bundle、trace、snapshot、audit sidecar 的引用与下载。
- 未来 API 在实现前必须先补齐 auth、tenant、storage、queue、rate limit、audit log 的 ADR 或 spec。
- `legacy-run`、benchmark、comparator 仍是 diagnostics/legacy 路径，不是未来 API 边界。

## Target Boundaries

### Job service

- 提交 research job
- 读取 job runtime projection
- 请求 cancel / retry
- 读取 event stream

### Artifact service

- 读取 report bundle
- 读取 trace
- 读取 source snapshot manifest
- 读取 claim graph 和 review queue

### Source and policy service

- 接收 source profile
- 执行 connector policy 和 fetch security
- 暴露 policy rejection reason

### Audit service

- 暴露 claim graph
- 暴露 critical claim review queue
- 暴露 `audit_gate_status`

## Consequences

- Phase 06 不会给用户带来新的 HTTP/API 命令。
- 当前 release gate 和 README 必须继续说明 CLI-first 事实。
- server implementation 进入下一 release train。
- 如果后续新增 server surface，必须先更新本 ADR、对应 spec 和 public surface 测试。

## Rejected Alternatives

### 在 Phase 06 直接实现 server

拒绝原因：

- 当前 storage/queue/auth/tenant 边界仍是 readiness 状态。
- 过早编码会固化 SQLite/subprocess/local path 形态。
- 会让文档把未来能力误写成当前能力。

### 直接把 legacy graph 包成 API

拒绝原因：

- legacy graph 仍服务 benchmark、comparator 和 hidden `legacy-run`。
- 未来 API 应围绕 public job runtime，而不是 legacy node graph。
