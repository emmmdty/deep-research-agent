import { useEffect, useState } from "react";
import { COMPETITORS, INDUSTRY_PAIN_POINTS } from "../data/competitors";
import { loadJson } from "../data";

interface AblationSummary {
  source: string;
  ablations: Array<{ id: string; name: string; scope: string; key_delta: string; interpretation: string }>;
}

interface HeadlineMetrics {
  metrics: Record<string, { value: number | string | null; sample_size?: number }>;
}

const HEADLINE_KEYS: Array<[string, string]> = [
  ["completion_rate", "任务完成率"],
  ["critical_claim_support_precision", "关键结论可支撑率"],
  ["citation_error_rate", "引用错误率"],
  ["policy_compliance_rate", "来源策略合规率"],
  ["resume_success_rate", "断点续跑成功率"],
];

const DESIGN_NOTES = [
  {
    question: "为什么要多智能体，而不是一个智能体带一堆工具？",
    answer:
      "任务特征决定选型：深度研究天然可并行（多个子主题互不依赖）、远超单次上下文窗口、需要多工具链——这正是 Anthropic 实测多智能体比单智能体高 90.2% 的任务类型。反例也存在（Anthropic 认为编码类任务多智能体未必更优），所以我们的结论是：研究场景多智能体成立，并且每个组件都通过消融实验验证了因果贡献，不是'智能体越多越高级'。",
  },
  {
    question: "为什么用任务图（DAG）编排，而不是自由流程？",
    answer:
      "备选方案包括线性流水线（简单但浪费并行性）和自由状态图（灵活但难以保证终止、做预算和恢复）。研究任务的结构本质是'规划一次 → 并行研究 → 汇总审核'，不需要任意循环，多轮追问用明确的上限和追问列表实现。DAG 因此可序列化（断点续跑）、可预算（每任务上限）、可审计（执行轨迹是产品产物）。",
  },
  {
    question: "为什么'结论要有出处'要作为执行规则，而不是事后补引用？",
    answer:
      "所有竞品都把引用当作报告生成后的装饰；我们把'每条关键结论必须绑定原始资料摘录'作为生成前的硬约束：绑不上出处的结论进人工复核，不进报告。消融实验证明这条规则的价值：关闭核对环节，无出处内容泄漏率升到 100%。",
  },
  {
    question: "模型怎么选？",
    answer:
      "系统不绑定单一模型：模型按角色配置（规划/研究/核对/写作可各用各的模型），带回退链和凭据加密。具体到每个角色该配哪个模型，是运行时配置项，由评测结果驱动——而不是在代码里写死。",
  },
];

export function AboutPage() {
  const [ablation, setAblation] = useState<AblationSummary | null>(null);
  const [headline, setHeadline] = useState<HeadlineMetrics | null>(null);

  useEffect(() => {
    loadJson<AblationSummary>("data/benchmarks/ablation_summary.json")
      .then(setAblation)
      .catch(() => setAblation(null));
    loadJson<HeadlineMetrics>("data/benchmarks/headline_metrics.json")
      .then(setHeadline)
      .catch(() => setHeadline(null));
  }, []);

  const metrics = headline?.metrics ?? {};

  return (
    <div className="page">
      <h2>关于本项目</h2>
      <p className="page-note">
        这是一个开源的深度研究系统。以下是它的设计思路、评测证据与行业对比——所有数字都来自
        仓库内已提交的评测产物，本地可复现（无需 API key）。
      </p>

      <section className="bench-section">
        <h3>设计思路：关键决策</h3>
        <div className="verdicts">
          {DESIGN_NOTES.map((d) => (
            <div className="verdict" key={d.question}>
              <h4>{d.question}</h4>
              <p>{d.answer}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>评测证据</h3>
        <div className="metric-grid">
          {HEADLINE_KEYS.map(([key, label]) => {
            const m = metrics[key];
            return (
              <div className="metric-cell" key={key}>
                <strong>{m ? String(m.value) : "…"}</strong>
                <span>{label}</span>
              </div>
            );
          })}
        </div>
        <p className="page-note">
          消融实验：单独关闭某个环节，观察可测的退化——这是"每个组件为什么存在"的直接证据。
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>关闭的环节</th>
              <th>退化表现</th>
            </tr>
          </thead>
          <tbody>
            {(ablation?.ablations ?? [])
              .filter((a) => a.id !== "provider_auto_vs_manual" && a.id !== "new_runtime_vs_legacy")
              .map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.name}</strong>
                    <div className="muted">{a.scope}</div>
                  </td>
                  <td>
                    <code>{a.key_delta}</code>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
        <p className="muted">
          来源：<code>{ablation?.source ?? "evals/reports/followup_metrics/ablation_summary.md"}</code>
        </p>
      </section>

      <section className="bench-section">
        <h3>与行业对比</h3>
        <p className="page-note">
          公开数字均标注来源（详见仓库 <code>docs/COMPETITIVE_LANDSCAPE.md</code>）。
          诚实声明：本项目的 live lane 数字来自真实 LLM + 实时搜索的已提交运行（GAIA 7/20，
          同模型无-agent baseline 0/20；头对头 vs open_deep_research / gpt-researcher 采用盲评 judge）；
          确定性本地评测只验证管线正确性，不与 live-provider 结果混用。
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>产品</th>
              <th>形态</th>
              <th>开源</th>
              <th>审计链</th>
              <th>基准信号</th>
            </tr>
          </thead>
          <tbody>
            {COMPETITORS.map((c) => (
              <tr key={c.product} className={c.product === "This project" ? "highlight-row" : ""}>
                <td>
                  <strong>{c.product === "This project" ? "本项目" : c.product}</strong>
                  <div className="muted">{c.reference}</div>
                </td>
                <td>{c.form}</td>
                <td>{c.openSource}</td>
                <td>{c.auditTrail}</td>
                <td>{c.benchmark}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bench-section">
        <h3>行业证据：多智能体协作为什么有效</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>来源</th>
              <th>发现</th>
              <th>我们的做法</th>
            </tr>
          </thead>
          <tbody>
            {INDUSTRY_PAIN_POINTS.map((p, i) => (
              <tr key={i}>
                <td className="muted">{p.source}</td>
                <td>{p.finding}</td>
                <td>{p.implication}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
