# 开发指南

## 环境搭建

```bash
# 克隆仓库
git clone https://github.com/emmmdty/deep-research-agent.git
cd deep-research-agent

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API 密钥
```

## 开发流程

### 新增 Agent

1. 在 `agents/` 下创建新文件（如 `agents/my_agent.py`）
2. 定义 LangGraph node 函数：接收 `state: dict` 返回 `dict`
3. 在 `workflows/graph.py` 中注册节点和边
4. 如需要，在 `workflows/graph.py` 的 `GraphState` 中添加新的状态字段

### 新增工具

1. 在 `tools/` 下创建新文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `tools/__init__.py` 中导出

### 新增提示词

1. 在 `prompts/templates.py` 中添加 `SYSTEM_PROMPT` 和 `USER_PROMPT`
2. User prompt 使用 `{variable}` 格式的占位符

### v1 现状审计提示词

- `prompts/project_audit.py` 提供 `build_v1_project_audit_prompt()` 和 `V1_PROJECT_AUDIT_PROMPT`
- 用于对当前仓库做“开源 v1 / 企业级定位”一致性审计，强制区分 `已实现`、`已声明但依赖配置/外部环境`、`占位或未接线`
- 该提示词还会强制检查目录结构和文件放置位置是否混乱，避免只审能力、不审工程边界
- 使用时需要把“静态检查结论”和“已实际运行验证”分开写，避免把未跑通的能力写成已验证

### 新增评估指标

1. 在 `evaluation/metrics.py` 中添加指标函数
2. 在 `evaluation/__init__.py` 中导出

## 常用命令

```bash
# 运行研究
uv run python main.py --topic "你的研究主题"

# 运行 Benchmark
uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba --max-topics 3

# 运行全量 comparator 对比
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba

# 离线文件对比
uv run python scripts/compare_agents.py --file-a our.md --file-b competitor.md
```

## 当前执行入口

- [90 天执行路线](./plans/90-day-execution-roadmap.md)
- [Gemini 能力差距分析](./plans/gemini-gap-analysis.md)
- [GitHub 长期项目化计划](./plans/github-long-term-plan.md)

说明：

- 当前真正的近期执行入口以 [90 天执行路线](./plans/90-day-execution-roadmap.md) 为准。
- `Gemini 能力差距分析` 用来约束“哪些后端能力值得追”，不是近期产品化目标清单。
- `GitHub 长期项目化计划` 用来约束长期治理，不应覆盖当前 90 天的实现优先级。

## 当前 90 天聚焦主线

只保留以下三条主线：

1. 统一运行工件与 comparator 结果契约
2. Critic 驱动的查询改写与多源支撑闭环
3. 最小真实性评测闭环

近期不应再新增新的能力大类。凡是不直接服务这三条主线的事项，默认后移。

## 近期暂缓 / 明确不做

- 暂缓 browser / document fetch 抽象层。
- 暂缓 claim graph / evidence graph。
- 暂缓公开 benchmark 排名或榜单目标。
- 暂缓社区运营扩张。
- 明确不做受支持 HTTP API。
- 明确不把 `mcp_servers/`、`memory/`、`skills/` 写成近期主能力。

## 文档同步清单

涉及 CLI、comparator、benchmark、架构边界、目录职责变化时，至少同步检查：

- `README.md`
- `README.zh-CN.md`
- `docs/architecture.md`
- `docs/development.md`
- `AGENTS.md`

如果某个目录、配置项或 comparator 仍处于“依赖外部环境”或“占位/未接线”，文档中必须明确标注，不能按默认已接通能力描述。

## 项目纪律

### 分支 / PR / Merge 规则

- 长期分支只保留 `main`。
- 短分支统一使用：`feat/*`、`fix/*`、`docs/*`、`chore/*`、`bench/*`。
- 合并策略统一为 `squash merge`。
- 提交信息继续使用中文 Conventional Commits。
- 一个 PR 只解决一个主题，验证命令与文档同步范围必须写清楚。

### Release 纪律

- 当前阶段继续使用 `v0.y.z`。
- 建议每 4-6 周一个 release 窗口。
- release 之前至少完成：
  - `uv run ruff check .`
  - `uv run pytest -q`
  - `uv run python main.py --help`
  - `uv run python scripts/run_benchmark.py --help`
  - `uv run python scripts/full_comparison.py --help`
- release note 必须明确：
  - 支持面变化
  - benchmark 变化
  - comparator 可验证范围
  - 已知限制

### Benchmark 发布最小格式

当前阶段，benchmark 结果优先作为内部工件维护；在运行工件和真实性口径稳定前，不要求每次 release 都公开完整 benchmark 摘要。

当需要对外发布 benchmark 结果时，至少包含：

- benchmark 范围（主题数量、任务集合、版本）
- comparator 覆盖情况
- 哪些结果是已验证能力
- 哪些结果依赖外部环境
- 哪些 comparator 允许 `skipped`
- 结果工件位置（如 `manifest`、JSONL 结果、摘要表）

## Release Note 模板

```md
# v0.y.z

## Summary
- 本次主要变化

## Supported Surface Changes
- CLI / benchmark / comparator / 文档边界的变化

## Benchmark
- 运行范围
- comparator 覆盖
- 关键结果

## Known Limits
- 依赖外部环境的能力
- 允许 skipped 的 comparator
- 仍未纳入主流程的目录或模块

## Verification
- uv run ruff check .
- uv run pytest -q
- uv run python main.py --help
- uv run python scripts/run_benchmark.py --help
- uv run python scripts/full_comparison.py --help
```

## 代码规范

- **Python**: 3.10+，使用类型注解
- **注释**: 中文
- **日志**: 使用 `loguru` 的 `logger.info/warning/error`
- **提交**: 中文 Conventional Commits（`feat:` / `fix:` / `docs:`）
