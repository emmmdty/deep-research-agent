# Phase 03: connector / source policy / snapshot / fetch security 重构

## 0. 文档状态
- 当前状态：active
- worktree：`/home/tjk/myProjects/internship-projects/dra-phase-03-connector-policy-security`
- branch：`refactor/phase-03-connector-policy-security`
- 基线提交：`f9cfff7`
- 最近更新：`2026-04-20T14:06:00Z`

## 1. 本 phase 解决的问题
- 对应审计问题：P1-1 allow/deny domain 只是候选过滤，不是 fetch 安全边界；P2-1 connector substrate 仍偏旧工具包装。
- 为什么现在先做这些：Phase 1/2 已收敛 runtime 可靠性；public collecting 阶段必须先避免明显不安全 URL 被 fetch。
- 如果不先做会发生什么：后续 API/web 允许用户输入 query/source 后，任意 URL、localhost、私网地址或非 HTTP scheme 可能绕过 candidate policy 进入 fetch。

## 2. 范围

### 2.1 改动目录
- `connectors/`
- `policies/`
- `agents/researcher.py`
- `tests/test_phase3_connectors.py`
- `docs/architecture.md`
- `docs/refactor/phase-03-connector-policy-security.md`

### 2.2 改动边界
- 会改什么：增加 fetch 前 URL 安全判定；阻止非 http(s)、localhost、loopback/private/link-local 等明显危险 host；让 collecting 在 fetch 前执行 policy。
- 不会改什么：不做 DNS 解析级 SSRF 防护，不实现集中 fetch proxy，不改 MCP sandbox，不扩展企业私有 connector。

### 2.3 非目标
- 非目标 1：不声称已具备企业级 outbound security。
- 非目标 2：不改变 report bundle wire shape。

## 3. 现状与问题
- 当前代码路径：`SourcePolicy.filter_candidates()` 只过滤 search candidate；`connectors.registry._web_fetch()` 直接调用 `web_scraper_tool`；`agents.researcher._collect_results()` fetch 前没有统一 fetch URI 安全检查。
- 当前行为：只要 candidate 进入 ordered items，fetch_fn 可能被调用。
- 当前缺陷：candidate policy 与 fetch policy 不是同一边界；明显危险 URL 没有统一拒绝原因。
- 对产品化 / 可靠性 / 安全性的影响：容易形成 SSRF/本机服务访问/非预期 scheme 抓取风险。

## 4. 设计方案

### 4.1 目标状态
- 目标 1：fetch 前统一阻止非 http(s)、localhost、私网/loopback/link-local host。
- 目标 2：被 fetch policy 拦截的来源不调用 connector fetch，并计入 connector health。
- 目标 3：web fetch adapter 自身也执行同一安全判定，避免绕过 researcher 路径。

### 4.2 方案描述
- 关键设计：在 `connectors.utils` 提供 URL 安全判定；`SourcePolicy` 暴露 `validate_fetch_uri()`；researcher fetch 前调用；`_web_fetch()` 作为 adapter 兜底检查。
- 状态模型变化：不新增长期 schema 字段；通过现有 `ConnectorHealthRecord.policy_blocked/error_count/last_error` 表达。
- 存储 / 接口 / 契约变化：不改变 artifact schema；被拦截来源不会生成 `SourceRecord` 或 snapshot。
- 对 legacy 的处理：legacy direct tools 不在本 phase 改造；public connector substrate 路径先加边界。

### 4.3 权衡
- 为什么不用方案 A：不做 DNS/redirect 复检，因为需要网络解析和集中 fetch proxy，超出本 phase。
- 为什么当前方案更合适：能在无新增依赖的情况下挡住最高风险的显式私网/本机/非 HTTP URL。
- 代价是什么：域名解析到私网 IP、redirect 到私网仍需后续集中 fetch proxy 处理。

### 4.4 回滚边界
- 可安全回滚的边界：revert 本 phase 对 connector/policy/researcher/tests/docs 的修改。
- 回滚后仍保持什么能力：Phase 1/2 runtime 不变量不受影响。
- 回滚会丢失什么：fetch 前 URL 安全拦截和测试保护。

## 5. 实施清单
- [x] 写失败测试：`SourcePolicy.validate_fetch_uri()` 拦截非 http(s)、localhost、私网 IP。
- [x] 写失败测试：`_web_fetch()` 拒绝私网/localhost URL。
- [x] 写失败测试：researcher collecting 不调用被 fetch policy 拦截的 connector fetch。
- [x] 实现 URL 安全判定和 SourcePolicy fetch validation。
- [x] 接入 researcher fetch 前检查与 connector health 记录。
- [x] 更新架构文档和本 phase 验证结果。

## 6. 实际修改

### 6.1 修改的文件
- `connectors/utils.py`
- `connectors/registry.py`
- `policies/source_policy.py`
- `agents/researcher.py`
- `tests/test_phase3_connectors.py`
- `docs/architecture.md`
- `docs/refactor/phase-03-connector-policy-security.md`

### 6.2 关键类 / 函数 / 状态字段变更
- 文件：`connectors/utils.py`
- 变更点：新增 `fetch_uri_block_reason()`，拒绝非 `http(s)`、localhost、loopback/private/link-local/unspecified/reserved IP。
- 原因：为 connector substrate 提供统一 fetch 前 URL 安全判定。
- 文件：`policies/source_policy.py`
- 变更点：新增 `FetchPolicyDecision` 和 `SourcePolicy.validate_fetch_uri()`，复用 URL 安全判定和 allow/deny domain。
- 原因：把 source policy 从 search candidate 过滤延伸到 fetch 前边界。
- 文件：`connectors/registry.py`
- 变更点：`_web_fetch()` 在调用 `web_scraper_tool` 前执行同一 URL 安全判定。
- 原因：避免绕过 researcher 路径直接调用 web adapter。
- 文件：`agents/researcher.py`
- 变更点：connector fetch 前调用 `policy.validate_fetch_uri()`；被拦截来源不调用 fetch，不生成 snapshot，并记录 `policy_blocked/last_error`。
- 原因：让 public collecting 路径真正执行 fetch policy。

### 6.3 兼容性与迁移
- 是否涉及数据迁移：预期不涉及。
- 是否涉及 artifact 变化：预期不改变 schema；被拦截 source 不会生成 snapshot。
- 是否影响 CLI / benchmark / comparator / legacy-run：影响 public connector substrate 的 fetch 行为；legacy-run direct path 不改。

## 7. 验收标准

### 7.1 功能验收
- [x] 合法 public HTTP/HTTPS source 仍可 snapshot。
- [x] Phase 3 现有 connector tests 仍通过。

### 7.2 失败路径验收
- [x] 非 http(s) scheme 被拦截。
- [x] localhost/loopback/private/link-local host 被拦截。
- [x] 被拦截 candidate 不调用 connector fetch。

### 7.3 回归验收
- [x] `uv run pytest -q tests/test_phase3_connectors.py`
- [x] `uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py`
- [x] `uv run pytest -q`
- [x] `uv run ruff check .`

### 7.4 文档验收
- [x] `docs/architecture.md` 更新 fetch security 当前事实。
- [x] `docs/refactor/phase-03-connector-policy-security.md` 写入实际修改和验证结果。

### 7.5 不变量验收
- [x] public runtime fetched source 必须通过 fetch policy 或 file ingest。
- [x] fetch policy 拦截不生成 snapshot。
- [x] 不把本 phase 写成完整企业级 SSRF 防护。

## 8. 验证结果

### 8.1 执行的命令
```bash
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase03-venv uv run pytest -q tests/test_phase3_connectors.py
UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase03-venv uv run pytest -q tests/test_phase2_jobs.py tests/test_phase4_auditor.py
uv run pytest -q
UV_CACHE_DIR=/tmp/uv-cache RUFF_CACHE_DIR=/tmp/ruff-cache UV_PROJECT_ENVIRONMENT=/tmp/dra-phase03-venv uv run ruff check .
```

### 8.2 结果
- 通过：基线 `tests/test_phase3_connectors.py`，`13 passed in 1.77s`。
- 通过：红绿后 `tests/test_phase3_connectors.py`，`16 passed in 1.12s`。
- 通过：`tests/test_phase2_jobs.py tests/test_phase4_auditor.py`，`28 passed in 2.00s`。
- 通过：`uv run ruff check connectors policies agents/researcher.py tests/test_phase3_connectors.py`，`All checks passed!`。
- 通过：`uv run pytest -q`，`164 passed in 5.60s`。
- 通过：`uv run ruff check .`，`All checks passed!`。
- 失败：当前暂无。
- 跳过：当前暂无。非提权 pytest 命令因仓库外 worktree 不能写 `.pytest_cache` 产生 warning；全量 pytest 使用提权验证通过。

### 8.3 证据
- 测试输出摘要：`13 passed in 1.77s`；`16 passed in 1.12s`；`28 passed in 2.00s`；`164 passed in 5.60s`；ruff 全量通过。
- 手工验证摘要：worktree 分支为 `refactor/phase-03-connector-policy-security`，起点为 `f9cfff7`。
- 仍存风险：DNS/redirect 级防护不在本 phase；后续需要集中 fetch proxy 或解析复检。

## 9. 合并评估
- 是否满足合并条件：满足。
- 若满足，建议如何合并：以普通 merge 回 `main`，保留 Phase 3 文档和实现提交。
- 若不满足，阻塞项是什么：无。

## 10. 合并后动作
- 需要更新的文档：`docs/refactor/000-overall-transformation-plan.md` 状态看板、`docs/architecture.md`。
- 需要同步的测试：Phase 4/5 继续把 fetch security 纳入 release gate。
- 下一 phase 进入条件：Phase 3 合并回 main，fetch policy 基线验收通过。

## 11. 复盘
- 本 phase 最大收益：public connector substrate 不再只在 search candidate 层过滤，fetch 前也有明确拒绝边界。
- 新发现的问题：`web_scraper_tool` direct legacy path 仍未集中治理；后续安全 phase 需要考虑 direct tool/MCP 入口。
- 是否需要回写总计划：需要，Phase 3 验收后回写状态看板和实际结果。
