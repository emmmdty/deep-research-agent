# Phase 12 — LongBench v2

## Objective
接入 LongBench v2 的 short / medium bucket，建立 long-context capability track。

## 必须完成
- MCQ adapter
- short bucket smoke
- medium bucket smoke harness
- bucket-aware manifests
- truncation / context-window diagnostics

## 需要新增
- `src/deep_research_agent/evals/external/benchmarks/longbench_v2/`
- `scripts/run_longbench_v2.py`
- `evals/external/configs/longbench_v2*.yaml`
- `docs/benchmarks/LONGBENCH_V2.md`

## 约束
- 不要强迫 LongBench v2 走 report-bundle official output
- official output 应是 MCQ prediction + official-style score
- internal bundle/trace 可以是 sidecar
- long bucket 允许只生成 challenge harness，不强制本 phase 跑 full

## Acceptance
- short smoke 运行成功
- medium bucket 至少有 smoke harness 或 blocked-with-reason
- overall / bucket / category accuracy 能产出
- truncation / bucket info 写入 diagnostics
- lint + focused tests 通过

## Validation
至少运行：
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- focused tests
- `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_longbench_v2.py --bucket short --subset smoke --output-root evals/external/reports/longbench_v2_short_smoke --json`
