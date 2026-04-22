# Phase 11 — LongFact / SAFE

## Objective
接入 LongFact / SAFE，建立开放域 long-form factuality regression 层。

## 必须完成
- LongFact dataset / prompt loader
- SAFE evaluator bridge
- search backend logging / cache
- subset smoke runner
- result manifests

## 需要新增
- `src/deep_research_agent/evals/external/benchmarks/longfact_safe/`
- `scripts/run_longfact_safe.py`
- `evals/external/configs/longfact_safe*.yaml`
- `docs/benchmarks/LONGFACT_SAFE.md`

## 约束
- 不得伪造 SAFE 分数
- 若搜索/评估 backend 不可用，输出 `null` 或 `blocked`，并记录原因
- 必须把搜索与 judge backend 写入 manifest

## Acceptance
- small subset smoke 可运行
- 至少输出 precision / recall / f1_at_k 或官方等价层
- internal diagnostics 也存在
- docs 写清成本与 drift 风险
- lint + focused tests 通过

## Validation
至少运行：
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_longfact_safe.py --subset smoke --output-root evals/external/reports/longfact_safe_smoke --json`
