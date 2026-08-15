# Evals

Canonical evaluation assets for the deterministic deep research runtime.

This tree is the Phase 5 source of truth for:

- suite definitions under `evals/suites/`
- frozen low-cost datasets under `evals/datasets/`
- rubric metadata under `evals/rubrics/`
- committed local smoke outputs under `evals/reports/`
- committed deterministic native regression outputs under `evals/reports/native_regression/`

The runnable local entrypoints are:

- `uv run python main.py eval run --suite company12`
- `uv run python main.py eval run --suite industry12`
- `uv run python main.py eval run --suite trusted8`
- `uv run python main.py eval run --suite file8`
- `uv run python main.py eval run --suite recovery6`
- `uv run python scripts/run_local_release_smoke.py`
- `uv run python main.py eval run --suite company12 --variant regression_local`
- `uv run python scripts/run_native_regression.py`
- `uv run python scripts/build_native_benchmark_summary.py`

## DRB（Deep Research Bench）官方评测

适配器：`src/deep_research_agent/evals/external/benchmarks/drb.py`，注册名为 `drb`
（`benchmark run --benchmark drb` 自动暴露）。引用真实性门禁：
`uv run python scripts/run_drb_gate.py`（阈值见 `evals/external/configs/drb_gate.yaml`，
scorecard 落 `evals/reports/drb_gate/scorecard.json`）。

### 官方数据集来源、许可与格式

- **论文**：Deep Research Bench: Evaluating AI Web Research Agents（FutureSearch，
  Bosse et al.，arXiv:2506.06287，2025-05）。**DRB-II**（rubric 式，132 任务/22 领域，
  9430 条细粒度 rubric）见 arXiv:2601.08536。
- **内容与格式**：多步开放网络研究任务，按任务类型分 8 类（Find Number / Find Dataset /
  Find Original Source / Validate Claim / Derive Number / Gather Evidence /
  Populate Reference Class / Compile Dataset）。每个实例配 10k-100k 网页的 **RetroSearch
  冻结语料**（模拟 Serper/Google 搜索形态，Common Crawl 兜底）与人工精修参考答案。官方评分：
  binary（0/1）、recall、F1、absolute difference（论文 Table 3）。
- **许可**：论文 CC BY-NC-SA 4.0。
- **获取方式**：官方出于防数据污染考虑**不公开全量实例**；评测运行需联系
  `evals@futuresearch.ai`，排行榜见 <https://drb.futuresearch.ai/>。
  仓库内 `evals/external/configs/drb_supported_smoke.yaml` +
  `evals/external/dataset_manifests/drb_supported_smoke.json` +
  `evals/datasets/drb_smoke_subset.yaml` 提供全离线 smoke 子集
  （评分模式对齐论文 Table 3），fixture bundle
  `evals/fixtures/drb/citation_fixture.json` 携带 `audit_summary.citation_verification`，
  供引用真实性门禁聚合。

### 引用真实性门禁

- 语义映射（固定常量，见 `scripts/run_drb_gate.py`）：`passed=verified`；
  `failed=unsupported+fetch_failed`；`unresolved=unverifiable`。
- `verified_rate = passed / (passed + failed + unresolved)`；
  分母为空时 `verified_rate=None` 判定为 blocked（reason `no_citation_evidence`）。
- 阈值从 `evals/external/configs/drb_gate.yaml` 读取（默认 `min_verified_rate: 0.9`），
  脚本不硬编码；低于阈值 CI job `drb-gate` 失败（非零退出码）。
