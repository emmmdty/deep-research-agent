# Resume Bullets

## 中文

- 基于 LangGraph 设计并实现可信研究型 LLM Agent，构建 `Supervisor / Planner / Researcher / Verifier / Critic / Writer` 工作流，打通 `web / github / arxiv / MCP / skills` 多能力路由与多轮补检索。
- 设计 `Verifier + Quality Gate` 证据闭环：对多源结果执行高可信来源优先、冲突识别、案例证据校验与失败阻断，避免将综述/聚合页伪装成已验证结论。
- 构建 `benchmark + ablation + hybrid release` 评测体系，输出 `research_reliability_score_100`、`system_controllability_score_100`、`benchmark_health` 等连续值指标，并支持 `ours_base / ours_verifier / ours_gate / ours_full` 变体对照。

## English

- Built a reliability-focused Deep Research agent on top of LangGraph with a `Supervisor / Planner / Researcher / Verifier / Critic / Writer` workflow and unified routing across `web / github / arxiv / MCP / skills`.
- Implemented a `Verifier + Quality Gate` pipeline to prioritize first-party evidence, detect conflicts, validate case-study signals, and block low-confidence runs instead of producing misleading “completed” reports.
- Designed a reproducible `benchmark + ablation + hybrid release` evaluation stack with continuous scorecards such as `research_reliability_score_100`, `system_controllability_score_100`, and `benchmark_health`, plus internal variants for measuring the gain from verification and gating.
