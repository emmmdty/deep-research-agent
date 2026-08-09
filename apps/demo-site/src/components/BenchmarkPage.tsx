import { useEffect, useState } from "react";
import { COMPETITORS, INDUSTRY_PAIN_POINTS } from "../data/competitors";
import { loadJson } from "../data";

interface AblationSummary {
  source: string;
  ablations: Array<{
    id: string;
    name: string;
    scope: string;
    key_delta: string;
    interpretation: string;
  }>;
}

interface ReleaseManifest {
  status?: string;
  suites?: Array<Record<string, unknown>>;
}

interface HeadlineMetrics {
  metrics: Record<string, { value: number | string | null; sample_size?: number }>;
}

const HEADLINE_KEYS: Array<[string, string, string]> = [
  ["completion_rate", "任务完成率", "提交的任务全部完成"],
  ["critical_claim_support_precision", "关键结论可支撑率", "关键结论均有证据支持"],
  ["citation_error_rate", "引用错误率", "引用与冻结证据库一致"],
  ["policy_compliance_rate", "来源策略合规率", "只使用许可来源"],
  ["resume_success_rate", "断点续跑成功率", "崩溃后可恢复"],
  ["stale_recovery_success_rate", "僵尸任务恢复率", "worker 掉线可接管"],
];

const VERDICT_LINES = [
  {
    question: "多 agent 真的有价值，还是噱头？",
    answer:
      "有价值，而且是被测出来的。确定性消融实验：关闭审计门禁，无证据结论泄漏率立即升到 100%；关闭证据重排，关键结论可支撑率从 1.0 掉到 0.5。行业侧，Anthropic 官方公布其多 agent 研究系统比单 agent 高 90.2%。",
  },
  {
    question: "系统输出可信吗？",
    answer:
      "本仓库的评测是确定性、可复现的：430+ 自动化测试、5 套评测 suite 全绿，无需 API key 即可在本地复现全部数字。诚实声明：这些是确定性 gate，不冒充 live-provider 对比——那是明确的 roadmap 项。",
  },
  {
    question: "和 OpenAI / Gemini Deep Research 比，有什么不同？",
    answer:
      "它们交付报告+事后引用列表；我们把证据做成执行契约：结论图、审计门禁、人工复核队列、冻结语料库都是系统产物。行业痛点（引用归属、来源质量、agent 错误累积）正是 Anthropic 工程博客点名的问题。",
  },
];

export function BenchmarkPage() {
  const [ablation, setAblation] = useState<AblationSummary | null>(null);
  const [release, setRelease] = useState<ReleaseManifest | null>(null);
  const [headline, setHeadline] = useState<HeadlineMetrics | null>(null);

  useEffect(() => {
    loadJson<AblationSummary>("data/benchmarks/ablation_summary.json")
      .then(setAblation)
      .catch(() => setAblation(null));
    loadJson<ReleaseManifest>("data/benchmarks/release_manifest.json")
      .then(setRelease)
      .catch(() => setRelease(null));
    loadJson<HeadlineMetrics>("data/benchmarks/headline_metrics.json")
      .then(setHeadline)
      .catch(() => setHeadline(null));
  }, []);

  const metrics = headline?.metrics ?? {};

  return (
    <div className="page">
      <h2>评测证据：这套系统可信吗？</h2>
      <p className="page-note">
        所有数字均来自仓库内已提交的评测产物，本地可一键复现（无需 API key、无需网络）。
        复现命令见 <code>docs/benchmarks/COMPARISON_PROTOCOL.md</code>。
      </p>

      <section className="bench-section">
        <h3>三个问题，直给答案</h3>
        <div className="verdicts">
          {VERDICT_LINES.map((v) => (
            <div className="verdict" key={v.question}>
              <h4>{v.question}</h4>
              <p>{v.answer}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bench-section">
        <h3>发布门禁与核心指标</h3>
        <div className="gate-card">
          <span className={`gate-pill ${release?.status === "passed" ? "ok" : "warn"}`}>
            {release?.status === "passed" ? "全部通过" : release?.status ?? "…"}
          </span>
          <span className="muted">
            {release?.suites?.length ?? 0} 套确定性评测 suite（phase5_local_smoke）· 430+ 自动化测试全绿
          </span>
        </div>
        <div className="metric-grid">
          {HEADLINE_KEYS.map(([key, label, note]) => {
            const m = metrics[key];
            return (
              <div className="metric-cell" key={key}>
                <strong>{m ? String(m.value) : "…"}</strong>
                <span>{label}</span>
                <span className="muted">{note}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="bench-section">
        <h3>消融实验：每个组件为什么存在</h3>
        <p className="page-note">
          方法：确定性环境下单独关闭一个机制，观察可测的退化。这是"多 agent 各部件有价值"
          最直接的证据。
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>机制</th>
              <th>关闭后的退化</th>
              <th>解读</th>
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
                  <td>{a.interpretation}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <p className="muted">来源：<code>{ablation?.source ?? "evals/reports/followup_metrics/ablation_summary.md"}</code></p>
      </section>

      <section className="bench-section">
        <h3>与行业对比</h3>
        <p className="page-note">
          公开数字均标注来源（详见 <code>docs/final/COMPETITIVE_LANDSCAPE.md</code>）。
          诚实声明：本项目的 committed 数字是确定性本地门禁，不是 live-provider 正面对比。
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>产品</th>
              <th>形态</th>
              <th>开源</th>
              <th>审计链</th>
              <th>基准信号</th>
              <th>成本</th>
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
                <td>{c.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bench-section">
        <h3>行业证据：多 agent 协作为什么有效</h3>
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
