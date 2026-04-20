# Legacy Benchmark Notes

## 定位

当前 benchmark / comparator 体系在迁移期内保留，但其定位已经调整为：

- 诊断 legacy runtime 的行为变化
- 提供历史样本与 regression seeds
- 暂时帮助比较迁移前后是否破坏现有能力

它们不再承担“产品是否可发布”的最终判据。

## 不再作为发布门槛的旧信号

- raw word count
- raw citation count
- section count
- keyword hit coverage
- “整篇报告看起来像不像研究报告”的单一 judge 分数

## 迁移期可保留的价值

- 作为 regression fixtures 的任务集与历史产物
- 对工具接入、CLI 输出、基本完整率的回归观察
- 对比 wrapper / adapter 是否破坏现有链路

## 后续替代方向

最终发布门槛应迁移到 `specs/evaluation-protocol.md` 中的 trust metrics：

- critical claim support precision
- citation error rate
- provenance completeness
- conflict handling
- uncertainty honesty
- completion / controllability / stability
- connector health / freshness / policy compliance
