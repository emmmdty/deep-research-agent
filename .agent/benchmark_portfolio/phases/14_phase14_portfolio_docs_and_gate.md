# Phase 14 — Portfolio summary / docs / gate integration

## Objective
把 benchmark portfolio 统一成清晰的 reviewer-facing 与 engineer-facing 产物，同时保持自建 benchmark 的 authoritative gate 地位。

## 必须完成
- `scripts/build_benchmark_portfolio_summary.py`
- `docs/benchmarks/README.md`
- `docs/benchmarks/PORTFOLIO.md`
- `docs/benchmarks/INTEGRITY.md`
- README benchmark section
- 现有 `docs/final/EXPERIMENT_SUMMARY.md` / `VALUE_SCORECARD.md` 适当链接 benchmark portfolio
- 统一 benchmark portfolio summary artifact

## 必须体现
- 哪些 benchmark 是 authoritative release gate
- 哪些是 secondary regression
- 哪些是 challenge track
- 哪些 deferred
- 当前哪些 adapters 已实现
- 当前哪些 runs 只是 smoke / subset
- 当前 integrity / capability caveats

## 约束
- 不得把 BrowseComp/GAIA 说成 authoritative gate
- 不得把当前 benchmark 接入包装成 production-grade benchmark service
- README 必须真实反映已实现状态

## Acceptance
- portfolio summary 可生成
- README / docs 更新完成
- final smoke on main 通过
- `git status --short` clean
- 当前自建 release gate 仍工作

## Validation
至少运行：
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- 当前 broad regression slice（从 `.agent/STATUS.md` 复用）
- 一个 native suite smoke
- 一个 external benchmark smoke
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_benchmark_portfolio_summary.py --output-root evals/external/reports/portfolio_summary --json`
- `git status --short`
