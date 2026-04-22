# Benchmark Portfolio Overlay

这个文件不是替换根目录 `AGENTS.md`，而是本次 benchmark integration run 的任务级补充指令。

## 本次 run 的唯一目标
在当前 `main` 基线上，为 Deep Research Agent 增加一套可维护、可分层、可复用的 external benchmark portfolio：

- FACTS Grounding
- LongFact / SAFE
- LongBench v2
- BrowseComp
- GAIA
- 自建 benchmark 继续作为 authoritative release gate

## 本次 run 的明确边界
- 不重跑旧的 Phase 0–9 架构迁移
- 不改项目定位
- 不做前端
- 不把 benchmark 逻辑塞进主 runtime
- 不用外部 benchmark 替代自建 release gate
- 不隐瞒 BrowseComp contamination / GAIA capability gap / LongBench v2 长上下文成本

## 本次 run 的 source of truth
优先级从高到低：
1. `.agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml`
2. `.agent/benchmark_portfolio/BENCHMARK_SPEC.md`
3. `.agent/benchmark_portfolio/PHASE_PLAN.md`
4. `.agent/benchmark_portfolio/IMPLEMENT.md`
5. `.agent/benchmark_portfolio/STATUS.md`
6. `.agent/benchmark_portfolio/phases/*`
7. 当前仓库已有的：
   - `README.md`
   - `FINAL_CHANGE_REPORT.md`
   - `docs/final/EXPERIMENT_SUMMARY.md`
   - `docs/final/VALUE_SCORECARD.md`
   - `evals/reports/phase5_local_smoke/release_manifest.json`
   - `AGENTS.md`
   - `.agent/STATUS.md`
   - `.agent/context/*`

## 本次 run 的关键判断
- benchmark integration 是评测层扩展，不是 runtime 重构
- 自建 benchmark 仍是 authoritative release gate
- FACTS Grounding 是第一优先级外部 regression
- LongFact/SAFE 是第二优先级 factuality regression
- LongBench v2 是 long-context track
- BrowseComp 与 GAIA 是 challenge / comparison track
- BrowseComp 必须加 integrity guard
- GAIA 必须 capability-gated
- LongBench v2 必须长度分桶
- 所有 benchmark 都要走统一 manifest / result / metric aggregation contract

## 产物优先级
本次 run 结束时，必须至少留下：
- benchmark adapter 代码
- benchmark runner 入口
- benchmark result manifests
- benchmark portfolio summary
- docs/benchmarks/*
- README 中的 benchmark portfolio 说明
- 对应 tests
