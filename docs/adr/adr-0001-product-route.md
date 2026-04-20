# ADR-0001: 产品路线采用“抽取可信研究核心 + 阶段性重建”

- Status: Accepted
- Date: 2026-04-09

## Context

当前仓库是 CLI-first 的 LangGraph 多智能体研究原型，已经具备研究流程、基础验证、来源工具和 benchmark/comparator harness，但与“可信深度研究 app”目标存在明显错位：

- 当前顶层边界仍是 agent 节点
- 当前验证与评测仍偏 report-first
- 当前缺少服务化 job runtime、claim-level 审核、连接器治理与产品级交付

## Decision

采用混合路线：

- 保留现有可迁移资产
- 抽取可信研究核心合同
- 以 phase 方式逐步重建产品骨架
- 不把现有多智能体图直接产品化

## Consequences

正向结果：

- 能保留现有工具、fixtures、测试文化和调试入口
- 能避免继续在错误边界上叠加复杂度
- 能把 schema、audit、policy、eval 先变成长期 source of truth

代价：

- 迁移期会同时维护 legacy runtime 与 future contracts
- 一部分文档需要显式区分“当前事实”和“目标架构”
- 旧 benchmark 结果会降级为 diagnostics

## Rejected Alternatives

### 纯增量演进

拒绝原因：

- 会把当前 graph-first 边界、启发式 verifier 和 report-shape 指标继续固化

### 推倒重来

拒绝原因：

- 会丢失现有 connectors、fixtures、调试入口与测试经验
- 会提高迁移期风险，且不利于逐 phase 验证
