# Interview Q&A

## 1. 为什么这不是一个普通的 RAG 项目？

因为系统的核心目标不是“把搜索结果拼进上下文”，而是“只让可信证据进入报告”。我单独引入了 `Verifier`、`Quality Gate` 和 case-study 证据分类：如果高可信来源不足，系统会终止为失败，而不是写一份看起来完整但实际不可靠的报告。

## 2. Verifier 和 Quality Gate 分别做了什么？

- `Verifier` 负责把来源转成结构化证据，做支持/弱支持/冲突标记，并维持实体一致性
- `Quality Gate` 负责把这些验证结果变成硬门槛，例如 case-study 必须有官方或一手仓库证据，否则不允许进入 Writer

两者组合起来，解决的是 Agent 系统里“能写”和“可信”之间的落差。

## 3. 为什么要支持 MCP 和 skills？

因为真实的 agent engineering 不会只停留在 prompt workflow。`skills` 适合封装稳定策略模板，`MCP` 适合接入外部工具生态。把两者都接进 capability registry 后，系统能根据任务类型和缺失方面选择合适能力，这比硬编码工具调用更接近生产环境里的 agent runtime。

## 4. 为什么最终结果集用 Hybrid release，而不是全量 live judge？

这是一个刻意做出的工程决策。全量 live judge 会引入更多外部波动，例如 API 限流、Judge 模型波动和搜索后端不稳定。`hybrid` 模式保留 3 个代表题的 live judge 校准，同时用全量 `portfolio12` 做可复现 benchmark 和 ablation，这样既能展示真实线上质量，也能保证结果可重复、可答辩。

## 5. 当前系统的真实短板是什么？

- 外部依赖波动仍会影响 `system_controllability_score_100`
- LLM summary 在某些 live 题型下仍可能弱化 selected evidence，需要靠 benchmark repair 兜底
- `portfolio12` 的 full-live 成本较高，因此正式展示采用 `hybrid` 而不是全量 live

这些限制没有被隐藏，而是通过 `benchmark_health`、`judge_status` 和 release manifest 显式暴露。
