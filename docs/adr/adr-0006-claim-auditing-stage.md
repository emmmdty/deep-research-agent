# ADR-0006: 公开 Runtime 增加 `claim_auditing` 阶段，并用 `completed + blocked` 表达审计门禁

- Status: Accepted
- Date: 2026-04-09

## Context

phase3 之后，公开 runtime 已经能稳定地产出 fetched document、snapshot 和 report bundle，但关键结论仍缺少 claim-level 审计边界。继续沿用 legacy `critic` 的任务级充分性评审，会把“研究够不够多”和“关键结论是否真的被证据支撑”混在一起。

## Decision

- 公开 orchestrator 在 `extracting` 后新增确定性阶段 `claim_auditing`
- `claim_auditing` 负责：
  - claim extraction
  - critical claim 标记
  - evidence linking
  - support / contradiction / unverifiable 判定
  - conflict set 生成
  - critical claim review queue
- 公开 runtime 的 stage 顺序调整为：
  - `created`
  - `clarifying`
  - `planned`
  - `collecting`
  - `extracting`
  - `claim_auditing`
  - `rendering`
  - `completed / failed / cancelled / needs_review`
- 未通过 full audit 的关键 claim 不再复用 `needs_review`，而是：
  - job `status = completed`
  - `audit_gate_status = blocked`
  - 报告、bundle、review queue 一并输出
- `needs_review` 继续只用于恢复和持久化异常
- legacy `critic` 仍保留给 legacy runtime / benchmark 路径，不再作为公开 runtime 的产品审计边界

## Consequences

- 关键结论的可信性从“任务级印象评分”变成可追踪的 claim graph
- 公开 CLI 和后续 UI 可以直接读取 blocked claims、review queue 与 audit artifacts
- legacy runtime 继续可运行，但不再代表可信研究产品边界
