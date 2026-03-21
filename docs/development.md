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
3. 在 `workflows/graph.py` 中注册节点和边；当前 benchmark 主链路默认包含 `Verifier`
4. 如需要，在 `workflows/graph.py` 的 `GraphState` 中添加新的状态字段

### 新增 Capability / Skill / MCP 适配

1. 在 `capabilities/` 中新增或扩展适配器
2. `builtin` 能力需要映射到真实 Python 工具
3. `skill` 兼容以 `SKILL.md` 为根的目录组织
4. `mcp` 当前优先从 `MCP_CONFIG_PATH` 指向的 YAML 配置加载，支持 `stdio / sse / streamable-http`；如未提供文件，再回退到 `MCP_SERVERS` JSON

### 新增 Verifier / Evidence Memory

1. Verifier 节点负责把 `SourceRecord` / `EvidenceNote` 转成 `EvidenceUnit`、`EvidenceCluster`
2. 持久化统一走 `memory/evidence_store.py`
3. 新增记忆或验证字段时，同步更新 `ReportArtifact` 与 benchmark 指标

### 新增工具

1. 在 `tools/` 下创建新文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `tools/__init__.py` 中导出

### 新增提示词

1. 在 `prompts/templates.py` 中添加 `SYSTEM_PROMPT` 和 `USER_PROMPT`
2. User prompt 使用 `{variable}` 格式的占位符

### 新增评估指标

1. 在 `evaluation/metrics.py` 中添加指标函数
2. 若指标需要 `Verifier / Evidence Memory / ReportArtifact` 信号，同步更新 `evaluation/comparators.py`
3. benchmark summary 现在区分 `scorecard`、`legacy_metrics` 与 `benchmark_health`，新增主展示指标时同步更新 `scripts/run_benchmark.py`
4. 如需比较方法收益，优先把变体接入 `scripts/run_ablation.py`，不要只在 README 中做口头描述
5. benchmark profile 下修改 `quality_gate` 时，必须同时校验 `failed_quality_gate` 终态与 comparator 失败语义，避免“gate 失败但仍 completed”
6. `case-study` 相关改动必须同时覆盖：query bundle、官方域名优先、GitHub 一手仓库识别、连续值指标与 summary 展示

## 常用命令

```bash
# 运行研究
uv run python main.py --topic "你的研究主题"
uv run python main.py --topic "你的研究主题" --profile benchmark

# 运行 Benchmark
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set local3 --summary
uv run python scripts/run_benchmark.py --comparators ours --profile benchmark --topic-set portfolio12 --summary

# 运行内部 ablation 对照
uv run python scripts/run_ablation.py --topic-set portfolio12 --profile benchmark

# 运行 portfolio12 正式 release（默认 hybrid：代表题 live judge + 全量可复现 benchmark）
uv run python scripts/run_portfolio12_release.py --env-file /绝对路径/.env --topic-set portfolio12 --release-mode hybrid

# 运行 local3 自动优化闭环
uv run python scripts/optimize_local3.py --profile benchmark --max-rounds 3 --skip-judge

# 运行全量 comparator 对比
uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba

# 离线文件对比
uv run python scripts/compare_agents.py --file-a our.md --file-b competitor.md
```

说明：
- `--summary` 会生成 `benchmark_summary.json/.md`
- 新版 summary 默认输出 `scorecard`、`legacy_metrics`、`benchmark_health` 和 `judge_status`
- `--skip-judge` 时，`judge_*` 不再写成 `0.0`，而是通过 `judge_status=skipped` 表达“本轮未评分”
- 若当前 worktree 没有本地 `.env`，通过 `--env-file` 显式加载主仓库或外部环境文件
- 正式结果集优先通过 `scripts/run_portfolio12_release.py` 产出；默认 `hybrid` 会对 `T01,T04,T11` 跑 live judge，并生成 `RESULTS.md` 与 `release_manifest.json`
- `case-study / 行业应用案例` 的 benchmark 方面默认只接受 `官方站点 + 一手仓库` 证据；survey / review / benchmark 结果应被拒绝为 `not_case_study_evidence`
- 相关 summary 应补充 `case_study_strength_score_100`、`first_party_case_coverage_100`、`official_case_ratio_100`、`case_study_gate_margin_100`
- benchmark profile 下，若 LLM summary 未满足方面/引用/高可信证据约束，会自动回退为 deterministic summary，并记录 `summary_repair_count`

## 代码规范

- **Python**: 3.10+，使用类型注解
- **注释**: 中文
- **日志**: 使用 `loguru` 的 `logger.info/warning/error`
- **提交**: 中文 Conventional Commits（`feat:` / `fix:` / `docs:`）
