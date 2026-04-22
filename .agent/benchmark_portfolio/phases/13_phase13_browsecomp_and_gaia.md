# Phase 13 — BrowseComp + GAIA

## Objective
以 challenge/comparison 轨接入 BrowseComp 与 GAIA，但必须显式处理 integrity / capability 风险。

## BrowseComp 必须完成
- short-answer adapter
- guarded subset smoke
- integrity guard:
  - benchmark_material_denylist
  - canary detection
  - query redaction
  - integrity report

## GAIA 必须完成
- capability matrix
- supported subset selector
- attachment/file handling bridge
- unsupported_capability reporting

## 需要新增
- `src/deep_research_agent/evals/external/benchmarks/browsecomp/`
- `src/deep_research_agent/evals/external/benchmarks/gaia/`
- `src/deep_research_agent/evals/external/integrity/`
- `scripts/run_browsecomp_guarded.py`
- `scripts/run_gaia_subset.py`
- `docs/benchmarks/BROWSECOMP.md`
- `docs/benchmarks/GAIA.md`
- `docs/benchmarks/INTEGRITY.md`

## 约束
- BrowseComp 必须 challenge-only，不进入 authoritative release gate
- GAIA 必须 subset-first，不允许把 unsupported 能力直接记成 benchmark failure
- 如果 gated dataset 无法在当前环境使用，必须写好 harness，并输出 blocked-with-reason

## Acceptance
- BrowseComp guarded smoke 可运行，且有 integrity report
- GAIA supported subset smoke 可运行，或完整 blocked report 存在
- docs 明确两者都不是 merge gate
- lint + focused tests 通过

## Validation
至少运行：
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_browsecomp_guarded.py --subset smoke --output-root evals/external/reports/browsecomp_guarded_smoke --json`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_gaia_subset.py --subset smoke_supported --output-root evals/external/reports/gaia_supported_smoke --json`
