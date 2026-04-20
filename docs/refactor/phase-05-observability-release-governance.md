# Phase 05: observability / release / config governance

## 0. 文档状态
- 当前状态：accepted
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-05-observability-release-governance`
- branch：`refactor/phase-05-observability-release-governance`
- 基线提交：`05f5637`
- 最近更新：`2026-04-20T15:40:40Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P2 benchmark / LLM judge 不能作为发布证明；P3 文档广度高于底层成熟度；P1 failure tests 需要进入 release gate。
- 为什么现在先做这些：Phase 1-4 已分别加固 runtime、connector security 和 audit grounding；现在需要把这些验收显式固化为 release gate，而不是继续让 benchmark runner 独自承担发布口径。
- 如果不先做会发生什么：`run_portfolio12_release.py` 仍可能产出 release manifest，但 manifest 只围绕 benchmark/judge/ablation，缺少 runtime lease、connector security、audit grounding、CLI/docs/current-surface 的发布门槛。

## 2. 范围

### 2.1 改动目录
- `configs/`
- `scripts/`
- `tests/`
- `docs/`
- `README.md`
- `README.zh-CN.md`

### 2.2 改动边界
- 会改什么：新增 release gate 配置与评估器；release manifest 纳入 runtime/security/audit/docs gates；README/development 文档说明 benchmark 只是 diagnostics，不能单独发布。
- 不会改什么：不运行 live benchmark，不引入外部监控 SaaS，不改变 comparator 算法，不新增 HTTP/API surface。

### 2.3 非目标
- 非目标 1：不做完整 SLO/observability 平台。
- 非目标 2：不把 release gate 写成已具备生产级多租户/API 能力。

## 3. 现状与问题
- 当前代码路径：`scripts/run_portfolio12_release.py` 构建 manifest 时只记录 preflight、benchmark、ablation、judge 和 env profile。
- 当前行为：release manifest 可以展示 benchmark health 与 scorecard，但没有结构化地要求 Phase 1-4 的可靠性/security/audit 回归。
- 当前缺陷：发布门槛仍容易被 benchmark 分数、quality gate pass rate 或 judge score 主导；config 也没有独立 release gate domain。
- 对产品化 / 可靠性 / 安全性的影响：后续对外叙述容易把 diagnostics 写成产品成熟度证明。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：新增 `configs/release_gate.yaml`，按 runtime、connector_security、audit_grounding、benchmark_diagnostics、docs_surface 分层定义必跑命令和证据。
- 目标 2：新增轻量 `scripts/release_gate.py`，可在无 heavy compute 下评估 manifest summary 是否满足 release gate。
- 目标 3：`run_portfolio12_release.py` 产出的 manifest 包含 release gate 结果，并在 `RESULTS.md` 中明确 benchmark 不是唯一发布依据。

### 4.2 方案描述
- 关键设计：release gate 默认要求非 benchmark 类 gate 存在且通过；benchmark diagnostics 只能作为一个分组，不能单独让 release gate 通过。
- 状态模型变化：不改变 job/runtime schema；只新增 release manifest 字段。
- 存储 / 接口 / 契约变化：`release_manifest.json` 增加 `release_gate` 字段；旧字段保持不变。
- 对 legacy 的处理：benchmark/comparator 仍保留 diagnostics 地位，不升级为产品发布证明。

### 4.3 权衡
- 为什么不用方案 A：不在本 phase 做真实外部监控或长时间 release pipeline，因为会扩大范围并引入环境依赖。
- 为什么当前方案更合适：先把 Phase 1-4 的可靠性/security/audit 验收固化为 release artifact，可用单元测试覆盖。
- 代价是什么：本 phase 的 release gate 仍是本地 manifest/checklist 级别，不是 CI 系统。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase 对 config/script/test/docs 的修改。
- 回滚后仍保持什么能力：Phase 1-4 runtime/security/audit 行为不受影响；旧 release runner 仍可运行。
- 回滚会丢失什么：manifest 中的 release gate 结构化结果和 README/development 的发布口径约束。

## 5. 实施清单
- [x] 写失败测试：只有 benchmark diagnostics 通过时 release gate 不能通过。
- [x] 写失败测试：release manifest 必须包含 runtime/security/audit/docs 分组。
- [x] 实现 release gate 配置与评估器。
- [x] 将 release gate 接入 `run_portfolio12_release.py` manifest / RESULTS。
- [x] 更新 README / development / phase 文档。

## 6. 实际修改

### 6.1 修改的文件
- `configs/release_gate.yaml`
- `scripts/release_gate.py`
- `scripts/run_portfolio12_release.py`
- `tests/test_release_gate.py`
- `tests/test_release_runner.py`
- `README.md`
- `README.zh-CN.md`
- `docs/architecture.md`
- `docs/development.md`
- `docs/refactor/phase-05-observability-release-governance.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`configs/release_gate.yaml`
- 变更点：新增 runtime、connector security、audit grounding、benchmark diagnostics、docs surface 五类必需 gate。
- 原因：把 Phase 1-4 的可靠性与安全验收纳入发布口径，避免 benchmark-only。
- 文件：`scripts/release_gate.py`
- 变更点：新增 `load_release_gate_config()`、`evaluate_release_gate()`、`build_release_gate_evidence()` 和 CLI。
- 原因：用可测试、可序列化的方式生成 release gate 结果。
- 文件：`scripts/run_portfolio12_release.py`
- 变更点：`release_manifest.json` 和 `RESULTS.md` 增加 `release_gate`。
- 原因：portfolio12 release diagnostics 产物明确展示哪些非 benchmark gate 缺失。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：预期不涉及。
- 是否涉及 artifact 变化：预期 `release_manifest.json` 增加可选 `release_gate` 字段。
- 是否影响 CLI / benchmark / comparator / legacy-run：benchmark runner 不改；portfolio12 release manifest 增强；legacy-run 不改。

## 7. 验收标准

### 7.1 功能验收
- [x] release gate 配置按 runtime/security/audit/benchmark/docs 分层。
- [x] release manifest 输出 `release_gate` 且保留旧 benchmark 字段。
- [x] RESULTS 明确 release gate 不是 benchmark-only。

### 7.2 失败路径验收
- [x] 只有 benchmark diagnostics 通过时 release gate 为 `blocked`。
- [x] 缺少必需 gate evidence 时 release gate 为 `blocked`。

### 7.3 回归验收
- [x] `uv run pytest -q tests/test_release_runner.py tests/test_scripts.py tests/test_phase4_auditor.py`
- [x] `uv run pytest -q`
- [x] `uv run ruff check .`
- [x] `uv run python scripts/run_benchmark.py --help`
- [x] `uv run python scripts/full_comparison.py --help`

### 7.4 文档验收
- [x] README 不把 benchmark 写成产品发布证明。
- [x] `docs/development.md` 增加 release gate 当前事实。
- [x] phase 文档写入实际验证结果。

### 7.5 不变量验收
- [x] 不新增 supported HTTP/API surface。
- [x] 不把 future CI/monitoring 写成当前能力。
- [x] benchmark/comparator 仍是 diagnostics/research tools。

## 8. 验证结果

### 8.1 执行的命令
```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_release_runner.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_release_gate.py tests/test_release_runner.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/test_release_gate.py tests/test_release_runner.py tests/test_scripts.py tests/test_phase4_auditor.py
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv uv run ruff check scripts/release_gate.py scripts/run_portfolio12_release.py tests/test_release_gate.py tests/test_release_runner.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_benchmark.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run python scripts/full_comparison.py --help
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv uv run ruff check .
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase05-venv PYTHONDONTWRITEBYTECODE=1 uv run python scripts/release_gate.py --help
```

### 8.2 结果
- 通过：基线 `tests/test_release_runner.py`，`1 passed in 1.21s`。
- 通过：红灯 `tests/test_release_gate.py tests/test_release_runner.py`，`3 failed`。
- 通过：红绿后 `tests/test_release_gate.py tests/test_release_runner.py`，`3 passed in 0.91s`。
- 通过：targeted 回归 `tests/test_release_gate.py tests/test_release_runner.py tests/test_scripts.py tests/test_phase4_auditor.py`，`15 passed in 1.94s`。
- 通过：新增脚本 targeted ruff，`All checks passed!`。
- 通过：`scripts/run_benchmark.py --help`、`scripts/full_comparison.py --help`、`scripts/release_gate.py --help`。
- 通过：`uv run pytest -q`，`167 passed in 9.47s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。

### 8.3 证据
- 测试输出摘要：基线 `1 passed in 1.21s`；红灯 `3 failed`；红绿 `3 passed in 0.91s`；targeted `15 passed in 1.94s`；全量 `167 passed in 9.47s`。
- 手工验证摘要：worktree 分支为 `refactor/phase-05-observability-release-governance`，起点为 `05f5637`。
- 仍存风险：release gate 仍是本地 manifest/checklist，不是外部 CI 或生产监控。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`，保留 Phase 5 文档和实现提交。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板。
- 需要同步的测试：Phase 6 API readiness 应继续沿用 release gate 中的 docs/API surface 检查。
- 下一 phase 进入条件：Phase 5 合并回 main，release gate 验收通过。

## 11. 复盘
- 本 phase 最大收益：release artifact 现在会明确显示 runtime/security/audit/docs gate，benchmark diagnostics 不再能单独代表发布。
- 新发现的问题：release gate 仍是本地 checklist；后续 Phase 6/API readiness 需要决定是否接入 CI 或外部 orchestrator。
- 是否需要回写总计划：需要，Phase 5 合并后回写状态看板和实际结果。
