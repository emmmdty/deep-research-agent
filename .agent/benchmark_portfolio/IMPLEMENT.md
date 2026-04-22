# Benchmark Portfolio Runbook

## 目的
本次 run 的任务是把 benchmark portfolio 接到当前 Deep Research Agent 上。
不是重做架构，不是重做 follow-up metrics。

## 读取顺序
在动手前按以下顺序读取：
1. `AGENTS.md`
2. `.agent/benchmark_portfolio/AGENTS_OVERLAY.md`
3. `.agent/context/PROJECT_SPEC.md`
4. `.agent/context/TASK2_SPEC.yaml`
5. `.agent/PREFLIGHT_DOC_AUDIT.md`
6. `.agent/STATUS.md`
7. `FINAL_CHANGE_REPORT.md`
8. `docs/final/EXPERIMENT_SUMMARY.md`
9. `docs/final/VALUE_SCORECARD.md`
10. `evals/reports/phase5_local_smoke/release_manifest.json`
11. `.agent/benchmark_portfolio/BENCHMARK_SPEC.md`
12. `.agent/benchmark_portfolio/BENCHMARK_PLAN_SPEC.yaml`
13. `.agent/benchmark_portfolio/PHASE_PLAN.md`
14. `.agent/benchmark_portfolio/STATUS.md`
15. 当前 phase 文件

## 运行原则
- 把当前 `main` 当 accepted baseline
- 不重跑旧 Phase 0–9
- 不改项目定位
- 不把 benchmark-specific 逻辑塞进主 runtime
- benchmark 逻辑只放进 `src/deep_research_agent/evals/external/` 与 `evals/external/`
- 自建 benchmark 继续是 merge-blocking release gate
- 外部 benchmark 先 smoke/subset，再考虑扩展

## Worktree 协议
每个 phase：
1. 先在 `main` 上复核上一阶段通过的 baseline
2. 新建 linked git worktree 和独立 branch
3. bootstrap worktree，显式检查 ignored/local-only 文件
4. 只做当前 phase
5. 运行 phase acceptance checks
6. 若通过：commit -> merge main -> main smoke -> remove worktree -> delete branch -> 更新 `.agent/benchmark_portfolio/STATUS.md`
7. 若失败：停在当前 worktree，修 phase 文件和 STATUS，重试
8. 每 phase 最多 4 次尝试
9. 若 4 次失败：停止整个 run，保留失败 worktree，输出 blocker report

## Worktree 命名
- branch: `codex/phase<NN>-<slug>/attempt-<N>`
- worktree: `../_codex_worktrees/phase<NN>-<slug>-attempt-<N>`

## Local-only 资产
每次新 worktree 后显式检查：
- `.env`
- `.venv`
- `.python-version`
- `workspace/`
- `.codex/`（如果存在）
- provider keys / benchmark cache / gated dataset cache
不要只看 `git status`。

## 统一输出纪律
所有 external benchmark 运行必须在 repo 内留下：
- machine-readable manifest
- human-readable README or RESULTS
- official score layer
- internal diagnostic layer

路径统一落在：
- `evals/external/reports/`
- `docs/benchmarks/`

## 验收原则
本次 run 的关键不是“都接上就算完”，而是：
- 有清晰 benchmark layering
- 有统一 adapter / runner / manifest
- 有最小可运行 smoke
- 不破坏当前自建 release gate
- 文档与代码一致
