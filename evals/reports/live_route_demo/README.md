# Live Route Demo — 杭州到东莞出行方案（persona 视角）

一次完整的 scheduler-v2 **agentic loop** 实况演示：真实 LLM + 真实检索（Tavily /
DuckDuckGo / 12306 官方页面全文抓取），回答一个**准确性要求很高**的真实出行问题，
并按三种 persona 给出路线选择依据。

## 演示问题

> 从杭州到东莞的出行路线方案对比（高铁、飞机、中转组合、自驾、大巴），
> 区分三种角色：普通旅客、持长龙航空 365 畅飞卡用户、持学生证的学生。

## Run Facts

| Field | Value |
| --- | --- |
| Job id | `20260814T090901Z-28016cbb` |
| Run date | 2026-08-14 (UTC) |
| Runtime | `scheduler-v2` canonical `ResearchScheduler` + `LLMResearchPlanner` |
| Researcher agents | 5 parallel `LLMResearcherWorker` tasks（agentic loop：function calling + 反思 + 全文阅读） |
| Critic agent | 1 `LLMCriticWorker`（矛盾审计 + 报告合成） |
| Model | `deepseek-v4-flash` via OpenAI-compatible endpoint（`LLM_DISABLE_THINKING=true`） |
| Search calls | 39 次 governed 检索（web/github/arxiv，经 `ToolGateway`） |
| Full-page reads | 20 个全文抓取（含 `kyfw.12306.cn` 学生票官方页面、携程列车/航班页） |
| 反思轮 | 3 个 researcher 任务各触发 1 轮覆盖度追问（共 3 次 `assess_coverage` 不足） |
| 产出 | 261 accepted claims / 1 qualified，98 个 frozen sources（83 snippet + 20 page_chunk） |
| 审计 | 无 unsupported claim 泄漏；报告末尾明确标注跨来源矛盾（车次清单、D3123 复用） |

## 关键结论（全部有 verbatim 证据 span 支撑）

- **高铁直达**：2026-08-15 杭州→东莞 8 个直达车次，首班 07:20 末班 21:10，
  最短 9h45m（D931 杭州东→虎门）；中转最快约 6h04m（G3087 杭州西 14:12 →
  惠州北 20:08 → G2747 → 东莞南 20:43，二等座合计约 ¥733）。
- **飞机**：东莞无民航机场，需经广州白云 / 深圳宝安中转；杭州→广州单程 ¥399 起
  （长龙航空 GJ8989 23:00 起 ¥650）、杭州→深圳 ¥480 起（GJ8737 08:50 → 11:05）。
  白云机场空港快线到东莞南城 75 分钟 ¥52；宝安机场高铁至虎门北 20–30 分钟。
- **长龙航空 365 畅飞卡**：售价 ¥365，全年不限次兑换国内自营航线经济舱 M 舱，
  每次仅另付 ¥266；航线覆盖广州、深圳 → **可用于杭州往返广州/深圳**。
  （该 persona objective 被模型规划器遗漏，由确定性覆盖校验自动补齐为第 5 个任务。）
- **高铁学生票**：每学年 4 次单程，动车组二等座/一等座/卧铺按执行票价 **7.5 折**
  （不低于公布票价 4 折），普速硬座 5 折；需 12306 资质核验，区间为家庭↔学校，
  退票返还次数。

## 准确性核验（人工 ground-truth 对照）

| 事实 | Agent 结论 | Ground truth（独立检索） | 一致 |
| --- | --- | --- | --- |
| 直达车次数量 | 8 个（2026-08-15） | trip.com 显示约 4–8 班区间 | ✓（报告标注来源差异） |
| 最快车程 | 直达 9h45m / 中转 6h04m | trip.com "最快 6 小时 4 分钟" | ✓ |
| 长龙 365 畅飞卡 | ¥365 不限次兑 M 舱 + 每次 ¥266 | 百度百科同款描述 | ✓ |
| 杭州↔深圳航线 | 长龙 GJ8737（08:50→11:05） | 长龙官方 2026-07-13 公示杭州萧山=深圳宝安航线 | ✓ |
| 学生票折扣 | 动车 7.5 折、普速硬座 5 折 | 12306 现行政策 | ✓ |
| 东莞无机场 | 需经广州/深圳中转 | 事实成立 | ✓ |

## 怎么复现

```bash
# .env 需配置 LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY，并设 LLM_DISABLE_THINKING=true
SCHEDULER_RUNTIME_MODE=production AGENT_PLANNER_ENABLED=true \
  uv run python scripts/run_live_demo.py
```

产物写到 `workspace/research_jobs/<job_id>/`（report.md / report_bundle.json /
run_summary.json / scheduler_checkpoints.json）。本目录为该次 run 的冻结快照。

## 诚实声明

- 票价、时刻、班次为 2026-08-14 检索到的第三方/官方页面内容，且已随时间变化；
  报告本身在"证据状态"部分标注了跨来源矛盾，要求以 12306 实时数据为准。
- 本演示展示的是 **agent 机制**（function calling 工具循环、覆盖度反思追问、
  全文阅读与分块 grounding、审计门禁），不构成出行购票建议。
