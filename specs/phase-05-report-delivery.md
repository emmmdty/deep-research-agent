# Phase 05 — Evidence-First Report Delivery

## Status

- Planned

## Objective

让交付物从“长文本报告”升级为“可展开、可导出、可复核的研究报告包”。

## Why This Phase Exists

到这一阶段，已经有稳定的 orchestrator、snapshot 和 claim graph，可以把用户真正感知到的可信研究体验显性化。

## Scope In

- report compiler
- evidence expansion
- conflict / uncertainty sections
- Markdown / HTML / PDF / report-bundle 导出
- time-to-first-finding surfaces

## Scope Out

- 复杂协同编辑平台
- 完整运营后台

## Required Deliverables

- `reporting/`
- report templates
- shareable bundle spec
- minimal review UI or viewer contract

## User-Facing Requirements

用户态报告至少包含：

- 结论摘要
- 关键发现
- 冲突与不确定性
- 方法与来源范围
- 附录：来源与执行摘要

每个关键结论必须支持展开到：

- 支撑证据片段
- 来源快照信息
- 相反证据或冲突说明
- claim 的审核状态

## Validation

- `20` 个任务的人审
- export fidelity tests
- evidence anchor click-through tests

## Metrics

- `100%` 关键结论可展开到 evidence anchors
- `ttff <= 120s`
- `ttfr p50 <= 20m`
- `ttfr p95 <= 30m`
- export consistency: `>=99%`

## Exit Criteria

- 用户无需看内部日志，也能审计报告里的关键结论
- 导出格式之间的证据锚点保持一致或有清晰退化策略

## Risks

- 不同导出格式的 citation anchor 一致性
- PDF fidelity 可能显著落后于 HTML

## Containment

若 PDF fidelity 不稳定，先把 HTML 作为审计首选格式，PDF 只做视图导出。
