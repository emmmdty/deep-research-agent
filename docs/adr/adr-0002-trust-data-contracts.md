# ADR-0002: 以 Claim / Evidence / Snapshot / Bundle 作为可信研究核心合同

- Status: Accepted
- Date: 2026-04-09

## Context

当前仓库的最小交付边界仍偏向“报告文本 + 来源列表”，但可信研究的最小可审计单元并不是 section 或 paragraph，而是 claim 以及它对应的 evidence 和 provenance。

## Decision

将以下对象提升为一等合同，并要求版本化 schema：

- `ResearchJob`
- `PlanStep`
- `SourceDocument`
- `SourceSnapshot`
- `EvidenceFragment`
- `Claim`
- `ClaimSupportEdge`
- `ConflictSet`
- `AuditEvent`
- `ReportBundle`

其中：

- `EvidenceFragment` 必须回到快照中的精确片段
- `Claim` 必须具备 support status、criticality、uncertainty
- `ReportBundle` 是交付、导出与评测的统一边界

## Consequences

- 报告生成必须转向 evidence-first，而不是 prose-first
- 审核逻辑必须围绕 claim support / contradiction / unverifiable 展开
- 任何新持久化对象都必须先补 schema

## Rejected Alternatives

### 继续以 section / paragraph 作为主要评估与交付单元

拒绝原因：

- 无法稳定承载 claim-level 审计与 provenance completeness

### 先实现功能，后补数据合同

拒绝原因：

- 会导致每个 phase 都绕回自由文本和隐式对象
