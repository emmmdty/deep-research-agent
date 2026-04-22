# Benchmark Portfolio Phase Plan

## Phase 10 — scaffolding + FACTS Grounding
目标：
- 建立 external benchmark substrate
- 新增 benchmark CLI / runner / manifest contract
- 接入 FACTS Grounding open subset（至少 smoke）
- 不破坏现有自建 release gate

完成定义：
- `main.py benchmark run --benchmark facts_grounding ...` 可用
- FACTS smoke 产出 official_scores + internal_diagnostics + benchmark_run_manifest
- 相关 tests / docs / schema 落地

## Phase 11 — LongFact / SAFE
目标：
- 接入 LongFact / SAFE
- 产出 subset smoke/regression harness
- 记录 search / judge backend 与成本说明

完成定义：
- subset smoke 可运行
- 结果有 fact-level outputs 和 summary
- 文档明确 LongFact/SAFE 的角色是 external factuality regression

## Phase 12 — LongBench v2
目标：
- 接入 LongBench v2 short / medium bucket
- 实现 MCQ adapter
- 做长度分桶与 truncation/capability 记录

完成定义：
- short smoke 可运行
- medium bucket 至少有 smoke harness
- long bucket 明确 deferred/challenge policy

## Phase 13 — BrowseComp + GAIA
目标：
- 接入 BrowseComp guarded subset
- 接入 GAIA supported subset
- 完成 BrowseComp integrity guard 与 GAIA capability matrix

完成定义：
- BrowseComp guarded smoke 可运行并产出 integrity report
- GAIA supported subset smoke 可运行并产出 capability-filter report
- 两者都不进入 merge gate

## Phase 14 — portfolio summary / docs / release integration
目标：
- 统一 benchmark portfolio summary
- 补充 docs/benchmarks/* 与 README benchmark section
- 将 external benchmark 融入现有 scorecard / experiment summary，但不替代自建 release gate

完成定义：
- `scripts/build_benchmark_portfolio_summary.py` 可运行
- `docs/benchmarks/README.md`
- `docs/benchmarks/PORTFOLIO.md`
- `docs/benchmarks/INTEGRITY.md`
- README 更新完成
