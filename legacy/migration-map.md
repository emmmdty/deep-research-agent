# Legacy Migration Map

本文件记录当前仓库中的主要资产，在目标可信研究架构下应如何处理。它的目标不是否定旧实现，而是避免“旧边界被默认继承为未来边界”。

## 边界说明

- 当前 `workflows/graph.py` 及相关 agent 节点属于 `legacy runtime`
- 当前 CLI 和 benchmark 脚本仍保留为迁移期可运行入口
- 未来 source of truth 以 `PLANS.md`、active phase spec、ADR、schema 为准

## 模块映射

| 当前资产 | 当前角色 | 未来建议归属 | 处理方式 |
|---|---|---|---|
| `main.py` | CLI 研究入口 | `gateway` 的开发/调试客户端 | 保留 |
| `workflows/graph.py` | LangGraph 主流程 | legacy runtime / 过渡执行路径 | 保留并显式标注 legacy |
| `agents/planner.py` | 任务拆解 | `PlanStep` 生成协议 | 保留概念，逐步去人格化 |
| `agents/researcher.py` | 多源收集 + 综合 | `collecting` / `extracting` / `synthesizing` 协议 | 高优先级拆分 |
| `agents/verifier.py` | 证据整理与粗验证 | `auditor` | 重构并并入审计管线 |
| `agents/critic.py` | 质量复评 | `auditor` / quality gate | 合并 |
| `agents/writer.py` | 报告撰写 | `reporting` / `ReportCompiler` | 降级为编译层能力 |
| `tools/web_search.py` | 网页搜索 | connector adapter | 保留并迁移 |
| `tools/github_search.py` | GitHub 搜索 | connector adapter | 保留并迁移 |
| `tools/arxiv_search.py` | arXiv 搜索 | connector adapter | 保留并迁移 |
| `research_policy.py` | 来源与质量策略 | `policy/` 下多个子模块 | 高优先级拆分 |
| `memory/evidence_store.py` | 证据持久化 | `evidence_store` | 保留概念，重做合同 |
| `evaluation/metrics.py` | 报告型指标 | `evals` trust metrics | 重构 |
| `evaluation/comparators.py` | comparator 协议 | diagnostics / migration tools | 保留但降级 |

## Keep / Refactor / Retire

### Keep

- 工具适配器与现有搜索入口
- CLI 调试入口
- benchmark fixtures、历史任务产物
- tests / ruff / pytest 文化

### Refactor

- `research_policy.py`
- `agents/researcher.py`
- `agents/verifier.py`
- `evaluation/metrics.py`
- `memory/evidence_store.py`

### Retire Or Downgrade

- 现有多 agent 图作为产品架构真相
- 报告长度、章节数、关键词命中作为核心质量指标
- deterministic repair 驱动的 benchmark 美化叙事
- “竞品没跑通所以我们赢了”的竞争结论
