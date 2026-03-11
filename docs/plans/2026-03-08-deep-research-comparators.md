# Deep Research Comparators Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将当前项目的 benchmark / comparison / competitor 接入改造成统一 comparator registry，并补齐结构化指标、回归测试与文档。

**Architecture:** 以 `evaluation/comparators.py` 作为统一执行层，所有系统都输出同一种 `ComparatorResult`。`scripts/run_benchmark.py` 与 `scripts/full_comparison.py` 只负责参数解析、主题遍历、结果落盘和终端展示，不再直接耦合具体竞品实现。已有 `run_research()`、`evaluate_report()`、`LLMJudge` 与结构化状态继续复用。

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, Rich, LangGraph, Loguru

---

### Task 1: Comparator 协议与配置入口

**Files:**
- Create: `evaluation/comparators.py`
- Modify: `configs/settings.py`
- Test: `tests/test_comparators.py`

**Step 1: Write the failing test**

验证 comparator registry 能解析启用列表、缺失配置时返回 `skipped`，并统一输出 `status / metrics / report_text` 字段。

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_comparators.py -q`
Expected: FAIL，因为 registry 与 comparator 协议尚不存在。

**Step 3: Write minimal implementation**

实现：
- `ComparatorMetrics`
- `ComparatorResult`
- `BenchmarkTopic`
- `run_comparator()`
- `resolve_comparators()`
- `load_topics()`

同时为 `ours / gptr / odr / alibaba / gemini` 提供最小可运行 adapter。

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_comparators.py -q`
Expected: PASS

### Task 2: Benchmark / full comparison 脚本迁移

**Files:**
- Modify: `scripts/run_benchmark.py`
- Modify: `scripts/full_comparison.py`
- Test: `tests/test_scripts.py`

**Step 1: Write the failing test**

验证 benchmark 聚合会：
- 使用统一 comparator 结果
- 输出 `aspect_coverage`
- 单个 comparator 失败不影响其它 comparator
- 支持可选 comparator `skipped`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scripts.py -q`
Expected: FAIL，因为脚本仍耦合旧版逻辑。

**Step 3: Write minimal implementation**

重写脚本内部函数，让 CLI 层基于 comparator registry 生成 JSON / Markdown 结果。

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scripts.py -q`
Expected: PASS

### Task 3: 评估与运行器回归

**Files:**
- Modify: `evaluation/llm_judge.py`
- Modify: `evaluation/metrics.py`
- Modify: `scripts/run_gptr_isolated.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

验证：
- pairwise judge 正确映射 X/Y 到 A/B
- `aspect_coverage` 与结构化 `source_records` 生效
- GPT Researcher runner 不再硬编码密钥

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_evaluation.py -q`
Expected: FAIL，因为旧接口或硬编码还存在。

**Step 3: Write minimal implementation**

修复解析、补充环境变量驱动配置、统一错误输出。

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_evaluation.py -q`
Expected: PASS

### Task 4: 文档与验收

**Files:**
- Modify: `README.md`
- Modify: `docs/development.md`
- Modify: `docs/architecture.md`
- Create: `pytest.ini`

**Step 1: Write the failing test**

无自动测试；以人工检查为主。

**Step 2: Run verification**

Run:
- `uv run pytest -q`
- `uv run python scripts/run_benchmark.py --help`
- `uv run python scripts/full_comparison.py --help`

Expected:
- 测试全绿
- 两个脚本都展示新 comparator 参数

