import { useEffect, useState } from "react";
import { Users, ShieldCheck, FileText } from "lucide-react";
import { AgentProcess } from "./AgentProcess";
import { ReportViewer, type ReportTab } from "./ReportViewer";
import { RUN_CASES, useBundle, useTrace } from "../data";

type DemoStep = "process" | "report" | "evidence";

const STEPS: Array<{ id: DemoStep; label: string; icon: React.ReactNode }> = [
  { id: "process", label: "1 · 多 agent 协作过程", icon: <Users size={15} /> },
  { id: "report", label: "2 · 交付的研究报告", icon: <FileText size={15} /> },
  { id: "evidence", label: "3 · 结论、证据与审计", icon: <ShieldCheck size={15} /> },
];

export function DemoPage() {
  const demo = RUN_CASES.find((c) => c.id === "demo-anthropic")!;
  const bundle = useBundle(demo.bundlePath);
  const trace = useTrace(demo.tracePath);
  const [step, setStep] = useState<DemoStep>("process");
  const [reportTab, setReportTab] = useState<ReportTab>("report");

  useEffect(() => {
    setStep("process");
    setReportTab("report");
  }, []);

  return (
    <div className="page">
      <h2>端到端演示：一个研究任务如何完成</h2>
      <p className="page-note">
        以"研究 Anthropic 公司"为例，走完系统的完整流程：三名研究员并行检索 →
        审稿人逐条审计证据 → 交付带证据链的研究报告。点击下方三个步骤逐步体验。
      </p>

      <div className="demo-question">
        <span className="muted">研究问题</span>
        <strong>研究 Anthropic 公司的产品线、商业模式与融资历程</strong>
        <span className="tag tag-demo">演示数据 · 确定性生成 · 无需 API key</span>
      </div>

      <div className="demo-steps">
        {STEPS.map((s) => (
          <button
            key={s.id}
            className={`demo-step-btn${step === s.id ? " active" : ""}`}
            onClick={() => setStep(s.id)}
          >
            {s.icon}
            {s.label}
          </button>
        ))}
      </div>

      {step === "process" && (
        <div className="step-panel">
          <p className="page-note">
            这是本次研究的执行轨迹（trace.jsonl，系统的一等公民产物）。播放动画可以看到：
            规划器先生成 3 个并行研究任务 → 三名研究员同时检索和提取证据 → 审稿人执行证据审计
            → 最终编译报告。
          </p>
          {trace ? (
            <AgentProcess events={trace} />
          ) : (
            <p className="muted">加载执行轨迹…</p>
          )}
        </div>
      )}

      {step === "report" && bundle && (
        <div className="step-panel">
          <p className="page-note">
            这是系统交付的研究报告——不是聊天式回答，而是带来源编号、可审计的正式文档。
          </p>
          <ReportViewer
            bundle={bundle}
            activeTab={reportTab}
            onTab={setReportTab}
            notice={
              <>
                <strong>演示说明：</strong>本案例为确定性生成的演示数据（基于 2025 年公开信息整理），
                用于在无 API key 时完整体验系统流程。真实运行需配置 LLM 与搜索凭据。
              </>
            }
          />
        </div>
      )}

      {step === "evidence" && bundle && (
        <div className="step-panel">
          <p className="page-note">
            这是本系统与"聊天式 AI"最本质的区别：<strong>每条结论都能展开查看它依据的证据</strong>。
            试着打开几条结论的证据：有证据支持的显示"支持"与置信度；只有背景信息的显示"仅有背景"；
            无证据的结论（如"与政府部门的合作传闻"）被审计门禁拦下，进入人工复核队列。
          </p>
          <ReportViewer bundle={bundle} activeTab="claims" onTab={() => undefined} />
        </div>
      )}
    </div>
  );
}
