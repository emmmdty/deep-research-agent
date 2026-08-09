import { useEffect, useState } from "react";
import { ArrowRight, Users, ShieldCheck, FileText } from "lucide-react";
import type { Tab } from "../App";

interface HeadlineMetrics {
  metrics: Record<string, { value: number | string | null; sample_size?: number }>;
}

const headlineCards: Array<{ key: string; label: string; note: string }> = [
  { key: "completion_rate", label: "任务完成率", note: "提交的研究任务成功完成" },
  { key: "critical_claim_support_precision", label: "关键结论可支撑率", note: "关键 claim 均能找到证据" },
  { key: "citation_error_rate", label: "引用错误率", note: "引用与冻结证据库一致" },
  { key: "policy_compliance_rate", label: "来源策略合规率", note: "只使用许可来源" },
];

export function HomePage({ navigate }: { navigate: (tab: Tab) => void }) {
  const [headline, setHeadline] = useState<HeadlineMetrics | null>(null);

  useEffect(() => {
    fetch("data/benchmarks/headline_metrics.json")
      .then((r) => r.json())
      .then(setHeadline)
      .catch(() => setHeadline(null));
  }, []);

  const metrics = headline?.metrics ?? {};

  return (
    <div className="home">
      <section className="hero">
        <h1>
          一支会<span className="accent">分工协作</span>、<span className="accent">逐条取证</span>的研究小组
        </h1>
        <p className="hero-sub">
          <strong>Deep Research Agent</strong> 是一个多 agent 深度研究系统：给它一个研究问题，
          系统像一支研究小组一样——规划任务、多名研究员并行检索、审稿人逐条核对证据、最后交付一份
          <strong>每条结论都能点开看证据</strong>的研究报告。
        </p>
        <div className="hero-actions">
          <button className="btn-primary" onClick={() => navigate("demo")}>
            看一个研究任务如何完成 <ArrowRight size={15} />
          </button>
          <button className="btn-secondary" onClick={() => navigate("reports")}>
            查看报告与证据
          </button>
          <button className="btn-secondary" onClick={() => navigate("benchmark")}>
            评测证据
          </button>
        </div>
      </section>

      <section className="how-it-works">
        <h2>它是怎么工作的</h2>
        <div className="flow">
          <div className="flow-step">
            <div className="flow-num">01</div>
            <h4>你提出问题</h4>
            <p>例如"研究 Anthropic 公司的产品线、商业模式与融资历程"</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">02</div>
            <h4>多名研究员并行工作</h4>
            <p>规划器把问题拆成子任务，3 名研究员 agent 并行检索、阅读来源、提取证据</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">03</div>
            <h4>审稿人逐条审计</h4>
            <p>critic agent 把每条结论与证据核对，无证据的结论被拦下进入人工复核</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">04</div>
            <h4>交付可审计报告</h4>
            <p>报告 + 结论清单 + 证据链 + 审计记录，机器可读、可复核、可追溯</p>
          </div>
        </div>
      </section>

      {Object.keys(metrics).length > 0 && (
        <section className="metric-strip">
          {headlineCards.map((c) => {
            const m = metrics[c.key];
            if (!m) return null;
            return (
              <div className="metric-card" key={c.key}>
                <div className="metric-value">{String(m.value)}</div>
                <div className="metric-name">{c.label}</div>
                <div className="metric-desc">{c.note}</div>
              </div>
            );
          })}
          <div className="metric-card">
            <div className="metric-value">430+</div>
            <div className="metric-name">自动化测试</div>
            <div className="metric-desc">CI 全绿，评测确定性可复现</div>
          </div>
        </section>
      )}

      <section className="pillars">
        <div className="pillar">
          <Users size={24} className="pillar-icon" />
          <h3>多 agent 协作，有证据</h3>
          <p>
            并行研究员 + 审稿人，任务图调度、类型化消息传递。价值由确定性消融实验证明：
            关掉审计门禁，无证据结论泄漏率升到 100%。
          </p>
        </div>
        <div className="pillar">
          <ShieldCheck size={24} className="pillar-icon" />
          <h3>审计优先，不是事后引用</h3>
          <p>
            每条关键结论必须指向冻结的证据快照；结论图、审计门禁、人工复核队列都是系统产出的
            一等公民工件，而不是报告里的装饰。
          </p>
        </div>
        <div className="pillar">
          <FileText size={24} className="pillar-icon" />
          <h3>生产级可靠性</h3>
          <p>
            任务可取消、重试、断点续跑、崩溃恢复；模型回退链、工具预算、凭据加密——agent
            系统在生产环境该有的工程能力，这里都有。
          </p>
        </div>
      </section>

      <section className="home-cta">
        <h2>想深入看？</h2>
        <div className="case-cards">
          <button className="case-card" onClick={() => navigate("demo")}>
            <strong>端到端演示</strong>
            <span>一个研究任务：规划 → 并行研究 → 审计 → 报告</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
          <button className="case-card" onClick={() => navigate("benchmark")}>
            <strong>评测证据</strong>
            <span>多 agent 有价值吗？消融实验 + 竞品对比</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
          <button className="case-card" onClick={() => navigate("architecture")}>
            <strong>技术实现</strong>
            <span>任务 DAG、调度器、治理网关、证据库</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
        </div>
      </section>
    </div>
  );
}
