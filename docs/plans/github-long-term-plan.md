生成日期：2026-03-15  
输入范围：当前仓库已跟踪的 GitHub 社区与治理相关文件（`.github/`、`README.md`、`README.zh-CN.md`、`AGENTS.md`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`docs/architecture.md`、`docs/development.md`、`tests/test_public_repo_standards.py`、`pyproject.toml`）、本地 git tag/commit 基线，以及少量官方 GitHub 仓库参考（`assafelovic/gpt-researcher`、`langchain-ai/open_deep_research`）。  
是否联网：是。  
当前仓库成熟度判断：Alpha 阶段，属于 CLI-first、benchmark-aware 的开源 v1 研究工程，正在从“可公开展示”向“可长期维护项目”过渡。  
当前治理基线：已有最小 CI、Issue/PR 模板、社区健康文件、`v0.1.0` 版本标签和基础包元数据；但 release 节奏、标签治理、benchmark 公布节奏、文档一致性检查、目录收束纪律和贡献者入口仍未制度化。  

# 当前 GitHub 项目化成熟度判断

结论：当前仓库已经具备“公开 GitHub 项目”的最低骨架，但还没有进入“长期维护、稳定发布、可持续吸引贡献者”的项目状态。更准确的说法是：**一个有明确边界、已有社区文件和基础 CI 的 Alpha 阶段研究工程仓库**。

## 当前已具备的项目化基础

- 已实现：社区健康文件齐全，包含 `CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、Issue 模板、PR 模板和 CI 工作流。
- 已实现：公共入口与边界相对清楚，`README.zh-CN.md` 与 `AGENTS.md` 都明确项目当前以 CLI-first 方式运行，没有受支持 HTTP API。
- 已实现：`tests/test_public_repo_standards.py` 已把部分公共仓库边界写成回归约束，例如主 CLI 不暴露服务端参数、`compare_agents.py` 只做离线文件比较。
- 已实现：`pyproject.toml` 有公开元数据、脚本入口和 `0.1.0` 版本号，本地 git 也已有 `v0.1.0` 标签。

## 当前治理的主要缺口

- 已声明但依赖外部环境：benchmark、外部 comparator、真实 research 运行依赖 `.env` 和外部服务，当前没有把“哪些结果是可验证的、哪些只是环境相关能力”制度化公开。
- 占位或未接线：`mcp_servers/`、`memory/`、`skills/` 等边缘目录仍可能在文档或结构理解上放大成熟度，但没有对应的长期治理规则去限制这种漂移。
- CI 过薄：当前 `.github/workflows/ci.yml` 仅跑 `uv sync --group dev`、`ruff check .`、`pytest -q`，不足以覆盖文档一致性、公共入口、benchmark 契约和版本发布纪律。
- release 仍是单点事件，不是持续节奏：当前只有 `v0.1.0`，还没有“何时发版、发什么、附带什么 benchmark 或文档校验结果”的固定流程。
- 社区入口还停留在“可提交 issue/PR”的最低层，没有 label 体系、triage 节奏、贡献难度分层，也没有稳定的 newcomer 入口。

## 对当前仓库最关键的判断

- 近期重点应该是**项目纪律**，不是社区运营扩张。
- 先把“什么是主线、什么是外部环境依赖、什么是占位/实验态”治理清楚，才值得扩大 contributor 面。
- 当前仓库最不该做的事，是在 release、README 或目录结构上继续扩张叙事，却不把主线、benchmark、comparator 和文档同步一起收束。

# 90 天计划

目标：把仓库从“有基础骨架的公开项目”推进到“有纪律、可持续发版、能让外部读者理解边界”的状态。

## 90 天核心任务

1. 建立公共支持面清单
   - 把 CLI、benchmark、comparator、文档、目录状态统一划分为 `已实现`、`依赖外部环境`、`占位/未接线`。
   - 把这套分类用作 README、架构文档、开发文档和 release note 的统一口径。
2. 建立 release 纪律
   - 继续使用 `v0.y.z`。
   - 90 天内至少形成一次稳定的发版节奏演练，目标是每 4-6 周一个 release 窗口。
   - release note 必须附“支持面变化、benchmark 变化、comparator 可验证范围、已知限制”。
3. 建立 branch / PR 纪律
   - 仅保留 `main` 为长期分支。
   - 统一短分支命名：`feat/*`、`fix/*`、`docs/*`、`chore/*`、`bench/*`。
   - 统一使用 squash merge，提交信息继续遵守中文 Conventional Commits。
4. 建立目录防漂移纪律
   - 新目录或新长期模块必须说明：职责、入口、是否主线、是否实验态、文档影响、测试影响。
   - 未进入主工作流的目录，不得在 README 主能力区按“已接线能力”叙述。
5. 建立文档同步纪律
   - 涉及 CLI/comparator/benchmark/架构的改动，必须同步检查 `README.md`、`README.zh-CN.md`、`docs/architecture.md`、`docs/development.md`、`AGENTS.md`。
   - release 前必须做一次 docs sync review。

## 90 天阶段交付

- 一套固定 release note 模板
- 一套固定 branch / PR / merge 纪律
- 一份“公开支持面清单”维护方法
- 一份 benchmark 结果最小公开格式
- 一份目录新增/升级前的治理检查清单

# 180 天计划

目标：把仓库从“有纪律”推进到“有稳定维护节奏、可对外展示持续改进”的状态。

## 180 天核心任务

1. 固化 monthly release 节奏
   - 从“偶发 release”升级为“至少每月 1 次 release”。
   - minor / patch 的边界固定下来：`y` 用于公共能力或 benchmark 契约升级，`z` 用于修复、文档同步、治理性收敛。
2. 建立 issue triage 机制
   - 每周至少 1 次 triage。
   - 固定最小 label 集合：`bug`、`enhancement`、`docs`、`benchmark`、`comparator`、`good first issue`、`help wanted`、`needs-repro`、`blocked/external-env`。
3. 建立 benchmark 发布机制
   - benchmark 不再只是脚本输出，而是 release 的固定组成部分。
   - 每次 release 至少附 benchmark 摘要、comparator 覆盖范围和可验证限制。
4. 建立文档例行审查
   - 每月一次文档一致性回顾。
   - 对主线目录与辅助目录进行一次“主线/实验态/占位”清点。
5. 建立贡献入口分层
   - `good first issue` 优先给文档修正、测试补全、benchmark 工件、preflight 改善。
   - `help wanted` 才逐步开放到低风险 comparator、研究流程改进或工具抽象。

## 180 天阶段交付

- 月度 release 节奏表
- label 与 triage 规则
- 固定 benchmark 发布模板
- 贡献任务分层入口
- 月度文档一致性 review 记录模板

# 365 天计划

目标：把仓库推进到“可长期维护、可持续发布、对外贡献入口稳定”的 GitHub 项目状态，但仍保持当前 CLI-first 研究工程边界，不强行扩成产品平台。

## 365 天核心任务

1. 稳定发布项目化
   - 连续 6 个月维持 monthly release。
   - release note 模板标准化，内容固定包含：公共行为变化、benchmark 结果、外部环境限制、已知兼容性。
2. benchmark-first 对外展示
   - README 与 release 页面固定展示最近一次 benchmark 摘要、当前 comparator 覆盖和未验证能力边界。
   - 不再只讲“能力愿景”，而要讲“当前可验证结果”。
3. 贡献者入口常态化
   - 让 newcomer 至少能从文档、测试、benchmark、comparator preflight 四类问题进入。
   - 把“容易误导读者的边界问题”转化成可独立贡献的治理任务。
4. 结构收束常态化
   - 每季度一次架构/目录审查。
   - 对长期未接线、无主线入口或无测试/文档支撑的目录或字段，做清理、降级叙述或标记实验态。
5. 条件式准备更高成熟度版本
   - 只有在 benchmark、docs sync、CI、外部 comparator 覆盖都稳定后，才考虑 `v1.0.0-rc`。
   - 不把“项目热度增长”当作进入 `v1` 的条件；以治理稳定度和支持面清晰度为准。

## 365 天阶段交付

- 连续稳定的 release 历史
- benchmark-first 的 README / release 展示方式
- 贡献者入口矩阵
- 季度结构审查机制
- `v1.0.0-rc` 进入条件清单

# Release 与版本策略

## 版本策略

- 当前阶段继续使用 `v0.y.z`，不提前切换到 `v1.x`。
- `y` 版本用于：
  - 公共支持面扩大或收缩
  - benchmark 契约或 comparator 覆盖变化
  - 重要工作流/文档边界调整
- `z` 版本用于：
  - bugfix
  - 文档同步
  - 非破坏性治理和测试增强

## branch / tag / release 节奏

- 长期分支：仅 `main`
- 短分支命名：
  - `feat/*`
  - `fix/*`
  - `docs/*`
  - `chore/*`
  - `bench/*`
- 合并策略：统一 `squash merge`
- tag 策略：所有 release 只从 `main` 绿灯状态打 tag
- 90 天内：每 4-6 周一个 release 窗口
- 180 天后：至少每月 1 次 release
- 365 天目标：保持 monthly release，并按季度做一次较大的整理型 minor release

## release 准入标准

每次 release 至少满足：

- `uv run ruff check .`
- `uv run pytest -q`
- `uv run python main.py --help`
- benchmark / comparator / docs sync 检查结论齐全
- release note 中明确写出：
  - 已实现能力
  - 依赖外部环境的能力
  - 占位或未接线能力
  - 本次 benchmark 结果或未发布原因

# Issue / PR / Branch 治理方案

## Issue 治理

- 保留现有 bug report / feature request 模板，不先扩复杂表单。
- 先补 label 体系，再谈更复杂的 automation。
- issue triage 规则：
  - `bug`：可复现缺陷
  - `enhancement`：明确的功能增强
  - `docs`：文档与公开支持面不一致
  - `benchmark`：数据集、结果、指标、发布问题
  - `comparator`：外部对比器接入或验证问题
  - `good first issue`：低风险、边界清晰
  - `help wanted`：需要外部贡献但不阻塞主线
  - `needs-repro`：信息不足
  - `blocked/external-env`：受外部 API、本地环境或配额阻塞

## PR 治理

- 延续当前 PR 模板的三段结构：
  - Summary
  - Verification
  - Notes
- 每个 PR 必须明确：
  - 改动类别
  - 验证命令
  - 是否涉及公开支持面
  - 是否需要文档同步
- 对长期维护更重要的是“小 PR 可审查”，不是一次 PR 打包多类变化。

## Branch 治理

- 不引入 `develop` 或其他长期分支。
- 每个分支只解决一个主题。
- branch 生命周期目标：
  - 7 天内合并或关闭
  - 超期分支必须重新确认是否仍值得维护

## 项目纪律优先级

- 第一优先级：branch / PR / release / docs sync 纪律
- 第二优先级：label / triage / newcomer 入口
- 第三优先级：更丰富的社区运营动作

# Benchmark 与文档发布机制

## benchmark 作为公开资产

- benchmark 不应继续只是内部脚本输出，而要成为 GitHub 项目的公开工件。
- 每次 release 应固定披露：
  - benchmark 运行范围
  - comparator 覆盖范围
  - 哪些 comparator 是已验证、哪些依赖外部环境、哪些允许 `skipped`
  - 本次结果与上次结果的主要变化

## 文档分层

- `README.md` / `README.zh-CN.md`
  - 只写公开支持面、快速入口、当前限制
- `docs/architecture.md`
  - 只写主线架构和明确纳入主流程的模块
- `docs/development.md`
  - 只写开发流程、验证方式、文档同步纪律
- `docs/plans/`
  - 存放长期治理与路线文档
- `docs/research/`
  - 存放竞争分析、路线研究等研究型文档

## 文档与 benchmark 的联动规则

- 公开行为变化未同步文档，不应发 release。
- benchmark 范围变化未写明 comparator 可验证边界，不应发 release。
- README 中不得把目录存在等同于能力已接入。
- 文档必须明确：
  - 已实现
  - 依赖外部环境
  - 占位/未接线

# 社区与贡献者入口设计

## 为什么当前仓库不应先做“社区运营”

- 当前最主要的问题不是“没人来贡献”，而是“外部贡献者进来后，很容易误解主线边界、comparator 成熟度和目录职责”。
- 因此先做项目纪律，比先做推广、discussion 活动或更复杂的互动机制更重要。

## 适合当前仓库的贡献入口

优先开放这四类任务：

- 文档同步与支持面收敛
- benchmark 工件与结果格式
- comparator preflight / 错误提示 / `skipped` 语义校验
- 测试补全与公共边界回归

其次再开放：

- 低风险搜索/研究流程改进
- 非主线的工具抽象
- 经过设计确认的小型 CLI 改进

## 外部参考为何适用

- `assafelovic/gpt-researcher`
  - 适用点：活跃 release、多个 workflow、dependabot、成熟贡献入口
  - 不适用点：其产品面和生态面远大于当前仓库，不能直接照搬
- `langchain-ai/open_deep_research`
  - 适用点：把 benchmark 结果直接公开到 README，并把实验结果和配置链路公开化
  - 不适用点：其 LangGraph server / Studio / OAP 形态并不适合当前仓库立即模仿

## 贡献者入口的建议节奏

- 90 天：只做纪律与入口清晰化
- 180 天：再系统化 `good first issue` 与 `help wanted`
- 365 天：当 release 与 benchmark 节奏稳定后，再扩大 contributor funnel

# 风险清单与防漂移机制

## 已确认事实

- 当前仓库已有基本社区健康文件和最小 CI。
- 当前仓库已有 `v0.1.0` 标签，但尚未建立 monthly release 节奏。
- 当前仓库已经明确是 CLI-first，没有受支持 HTTP API。
- 当前 comparator 与 benchmark 能力存在，但外部 comparator 大量依赖本地环境或导入目录。
- 当前目录结构主线清楚，但边缘目录和文档边界仍可能误导外部贡献者。

## 未验证假设

- 当前仓库是否会持续收到足够多的 issue/PR，需要更多月份数据才能判断。
- 外部 comparator 在未来 6-12 个月内能否稳定验证到 `3/4`，取决于环境可得性和维护者时间投入。
- 当前 maintainer 是否有足够时间维持 monthly release，需要按真实节奏再校准。

## 风险清单

1. 目录膨胀，但主线和文档没有同步收束。
2. benchmark 与 comparator 叙事再次超前于真实可验证范围。
3. CI 只验证代码基本健康，不验证公共支持面与文档一致性。
4. release 继续偶发发生，导致外部读者无法形成稳定预期。
5. 过早扩大贡献入口，导致维护者时间被低质量问题和误解性 PR 消耗。
6. 外部 comparator 受环境阻塞，长期拖累 public claim 的可信度。

## 防漂移机制

- 新目录、新模块、新长期配置项必须说明：
  - 入口在哪里
  - 是否主线
  - 是否实验态
  - 需要哪些测试与文档同步
  - 若长期未接线，何时降级或清理
- 每季度做一次“主线 / 辅助 / 占位”清点。
- 每次 release 前做一次 docs sync 审查。
- 所有 benchmark 公开结果都必须标明：
  - 已验证
  - 依赖外部环境
  - 允许 `skipped`

## 下一步执行顺序

1. 先建立 release note 模板和 docs sync checklist。
2. 再建立 label / triage / branch / merge 纪律。
3. 然后把 benchmark 发布流程纳入每次 release。
4. 再整理 contributor 入口与 `good first issue`。
5. 最后才考虑更大范围的社区运营动作。

## 长期维护最小治理清单

1. `main` 是唯一长期分支，所有工作走短分支。
2. 所有合并统一 squash merge，提交信息使用中文 Conventional Commits。
3. 每次 release 必须附 release note 和 benchmark 摘要。
4. README 与核心 docs 不同步，不发 release。
5. 未接线目录和配置不得在公开文档中按已实现能力描述。
6. 所有 benchmark / comparator 结果必须标明已验证、依赖环境或允许 `skipped`。
7. 每周至少一次 issue triage。
8. 每月一次文档一致性回顾。
9. 每季度一次目录与架构收束审查。

# KPI 指标表

| 指标 | 当前基线 | 90 天目标 | 180 天目标 | 365 天目标 | 说明 |
|---|---|---:|---:|---:|---|
| 每月 release 频率 | 历史仅 1 次公开 release / 1 个标签 | >= 0.5 次/月 | >= 1 次/月 | 稳定 1 次/月 | 以 GitHub release 为准 |
| CI 成功率 | 未建立历史统计 | >= 90% | >= 95% | >= 97% | 以默认 CI workflow 为准 |
| pytest / lint 稳定性 | 本地已验证一次通过 | >= 95% PR 通过 | >= 97% PR 通过 | >= 98% PR 通过 | 以 `ruff + pytest` 为准 |
| 文档一致性检查覆盖率 | 未制度化 | >= 80% | >= 95% | >= 98% | 指关键文档是否纳入 release 前检查 |
| benchmark 公开发布频率 | 未建立固定节奏 | 每 2 个月 >= 1 次 | 每月 >= 1 次 | 每月 >= 1 次，且季度汇总 | 以公开结果摘要为准 |
| issue 首响时间 | 未建立 SLA | <= 120 小时 | <= 72 小时 | <= 48 小时 | 首次 maintainer 响应时间 |
| PR 平均合并周期 | 未建立 SLA | <= 21 天 | <= 14 天 | <= 10 天 | 以非 blocked PR 计 |
| 回归测试数量增长目标 | 34 | 45+ | 60+ | 80+ | 以 `tests/` 中回归测试为准 |
| 外部 comparator 可验证覆盖率 | 0/4 | >= 1/4 | >= 2/4 | >= 3/4 | 不含 `ours`，只算外部 comparator |
| README 与 docs 的同步完成率 | 部分一致，未制度化 | >= 85% | >= 95% | >= 98% | 以 release checklist 结果为准 |

说明：

- 表中多项“当前基线”为治理现状，不是质量指标统计结果；因为当前仓库还没有形成足够长的公开维护历史。
- `外部 comparator 可验证覆盖率` 的目标是治理目标，不等于承诺所有 comparator 都默认开箱即用。

# 更新记录

| 日期 | 输入范围 | 是否联网 | 本次新增/修订重点 | 与上版差异 |
|---|---|---|---|---|
| 2026-03-15 | 当前仓库 `.github`、README、AGENTS、社区文件、docs、tests、pyproject、git tag/commit 基线，以及 `gpt-researcher`、`open_deep_research` 官方 GitHub 仓库元数据 | 是 | 首版 GitHub 长期项目化三阶段方案 | 首次创建，无上版 |
