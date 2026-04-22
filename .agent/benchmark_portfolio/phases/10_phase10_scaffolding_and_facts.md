# Phase 10 — Benchmark scaffolding + FACTS Grounding

## Objective
建立 external benchmark integration substrate，并优先接入与当前 claim/evidence/audit 最同构的 FACTS Grounding open subset。

## 必须完成
- 新增 `src/deep_research_agent/evals/external/`
- 新增 benchmark contracts / registry / manifests
- 新增 benchmark CLI surface，例如：
  - `main.py benchmark run --benchmark facts_grounding ...`
- 新增 FACTS Grounding adapter
- 新增 public/open subset smoke harness
- 不破坏现有 `eval run --suite ...`

## 需要新增的内容
- `src/deep_research_agent/evals/external/contracts.py`
- `src/deep_research_agent/evals/external/registry.py`
- `src/deep_research_agent/evals/external/manifests.py`
- `src/deep_research_agent/evals/external/benchmarks/facts_grounding/`
- `evals/external/configs/facts_grounding*.yaml`
- `scripts/run_external_benchmark.py`
- `scripts/run_facts_grounding.py`
- benchmark schemas
- docs/benchmarks/FACTS_GROUNDING.md

## 接口要求
FACTS run 至少产出：
- `benchmark_run_manifest.json`
- `official_scores.json`
- `internal_diagnostics.json`
- `task_results.jsonl`
- `README.md`

## 约束
- 必须保留 repo-native internal diagnostics
- 但 official FACTS score 不得被自定义指标替代
- 先跑 open/public subset
- private/blind split 只写好 harness/notes，不在本 phase 强推

## Acceptance
本 phase 通过条件：
- 新 benchmark runner surface 可用
- FACTS Grounding smoke subset 能跑通
- manifest / score / diagnostics 产物齐全
- lint + focused tests 通过
- 现有自建 release gate 不受破坏

## Validation
至少运行：
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- 新增 benchmark contracts/adapters 的 focused tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python main.py benchmark run --benchmark facts_grounding --split open --subset smoke --output-root evals/external/reports/facts_grounding_smoke --json`
- 现有 `eval run --suite company12` 或等价 smoke 验证主 gate 未破坏
