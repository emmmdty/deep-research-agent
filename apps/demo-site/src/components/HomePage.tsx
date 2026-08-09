import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import type { Tab } from "../App";

const SUGGESTED_QUESTIONS = [
  "研究 Anthropic 公司的产品线、商业模式与融资历程",
  "研究同花顺这家公司的基本面和业务",
  "DeepSeek-V4 的架构有哪些关键技术？",
];

export function HomePage({
  startResearch,
  navigate,
}: {
  startResearch: (question: string) => void;
  navigate: (tab: Tab) => void;
}) {
  const [input, setInput] = useState("");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (text) startResearch(text);
  }

  return (
    <div className="home">
      <section className="hero">
        <h1>
          问一个研究问题，<br />
          得到一份<span className="accent">每条结论都有出处</span>的报告
        </h1>
        <p className="hero-sub">
          Deep Research Agent 是一个深度研究助手：输入问题后，多名研究员并行检索资料、
          核对证据、撰写报告——就像一支真正的研究小组在工作。
        </p>

        <form className="ask-box" onSubmit={submit}>
          <textarea
            className="ask-input"
            placeholder="例如：研究 Anthropic 公司的产品线、商业模式与融资历程"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
          />
          <button className="btn-primary ask-submit" type="submit" disabled={!input.trim()}>
            开始研究 <ArrowRight size={16} />
          </button>
        </form>

        <div className="suggestions">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button key={q} className="suggestion-chip" onClick={() => startResearch(q)}>
              <Sparkles size={12} /> {q}
            </button>
          ))}
        </div>
      </section>

      <section className="how-it-works">
        <h2>你的研究任务会经历这些步骤</h2>
        <div className="flow">
          <div className="flow-step">
            <div className="flow-num">01</div>
            <h4>理解问题</h4>
            <p>系统判断问题范围，规划研究计划</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">02</div>
            <h4>并行研究</h4>
            <p>多名研究员同时检索、阅读来源、提取要点</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">03</div>
            <h4>核对证据</h4>
            <p>每条结论与原始资料核对，没有出处的结论会被拦下</p>
          </div>
          <ArrowRight size={18} className="flow-arrow" />
          <div className="flow-step">
            <div className="flow-num">04</div>
            <h4>撰写报告</h4>
            <p>交付研究报告，每条结论都可以点开看来源</p>
          </div>
        </div>
      </section>

      <section className="pillars">
        <div className="pillar">
          <h3>不只是聊天式回答</h3>
          <p>
            交付的是结构化研究报告：结论、引用来源、审核记录一应俱全，可存档、可复核、
          可程序化消费。
          </p>
        </div>
        <div className="pillar">
          <h3>结论都有出处</h3>
          <p>
            每条关键结论都链接到原始资料的摘录。查不到出处的内容不会出现在报告里，
            而是进入人工复核流程。
          </p>
        </div>
        <div className="pillar">
          <h3>可中断、可恢复</h3>
          <p>
            研究任务随时可取消、可续跑，进度不会丢失——适合长时间运行的深度研究。
          </p>
        </div>
      </section>

      <section className="home-cta">
        <h2>想了解更多？</h2>
        <div className="case-cards">
          <button className="case-card" onClick={() => navigate("research")}>
            <strong>发起一项研究</strong>
            <span>体验完整的研究流程</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
          <button className="case-card" onClick={() => navigate("reports")}>
            <strong>查看示例报告</strong>
            <span>几份不同主题的真实产物</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
          <button className="case-card" onClick={() => navigate("about")}>
            <strong>关于本项目</strong>
            <span>设计思路、评测证据与竞品对比</span>
            <ArrowRight size={14} className="case-arrow" />
          </button>
        </div>
      </section>
    </div>
  );
}
