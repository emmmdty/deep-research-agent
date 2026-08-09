import { useMemo, useRef, useState } from "react";
import { ArrowUp, BookOpen } from "lucide-react";
import { ResearchProgress } from "./ResearchProgress";
import { ReportViewer, type ReportTab } from "./ReportViewer";
import { RUN_CASES, useBundle, useTrace } from "../data";
import type { RunCase } from "../data/types";

function matchCase(question: string): RunCase {
  const q = question.toLowerCase();
  if (q.includes("anthropic") || q.includes("claude") || q.includes("克劳德")) {
    return RUN_CASES.find((c) => c.id === "demo-anthropic")!;
  }
  if (q.includes("同花顺") || q.includes("300033")) {
    return RUN_CASES.find((c) => c.id === "ths-20260522")!;
  }
  if (q.includes("deepseek")) {
    return RUN_CASES.find((c) => c.id === "dsv4-20260425")!;
  }
  if (q.includes("openai")) {
    return RUN_CASES.find((c) => c.id === "company-openai-surface")!;
  }
  return RUN_CASES.find((c) => c.id === "demo-anthropic")!;
}

type Phase = "input" | "researching" | "report";

export function ResearchPage({ question }: { question: string }) {
  const [input, setInput] = useState(question);
  const [activeQuestion, setActiveQuestion] = useState(question);
  const [phase, setPhase] = useState<Phase>(question ? "researching" : "input");
  const [reportTab, setReportTab] = useState<ReportTab>("report");
  const [followUp, setFollowUp] = useState("");
  const doneRef = useRef(false);

  const activeCase = useMemo(() => matchCase(activeQuestion), [activeQuestion]);
  const bundle = useBundle(activeCase.bundlePath);
  const trace = useTrace(activeCase.tracePath);

  function submit(text: string) {
    if (!text.trim()) return;
    setActiveQuestion(text.trim());
    setInput(text.trim());
    setPhase("researching");
    setReportTab("report");
    doneRef.current = false;
    window.scrollTo({ top: 0 });
  }

  function onProgressDone() {
    doneRef.current = true;
    setPhase("report");
  }

  function followUpSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(followUp);
    setFollowUp("");
  }

  const isDemo = activeCase.tag === "demo";
  const notice = isDemo ? (
    <>
      <strong>演示模式：</strong>当前在线体验使用演示数据（基于 2025 年公开信息整理）。
      真实版本会在你的研究任务中使用实时检索与模型。
    </>
  ) : activeCase.tag === "real" ? (
    <>
      <strong>真实运行产物：</strong>这是一次真实调度的运行记录。受当时检索条件限制，
      部分内容未通过证据核对——这也展示了系统的严谨性。
    </>
  ) : (
    <>
      <strong>演示数据：</strong>用于展示报告形态的合成示例。
    </>
  );

  return (
    <div className="page research-page">
      <h2>发起研究</h2>

      <form
        className="research-ask"
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
      >
        <textarea
          className="ask-input"
          placeholder="输入你的研究问题，例如：研究 Anthropic 公司的产品线、商业模式与融资历程"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={2}
        />
        <button className="btn-primary ask-submit" type="submit" disabled={!input.trim()}>
          开始研究 <ArrowUp size={15} />
        </button>
      </form>

      {phase === "researching" && (
        <div className="step-panel">
          <p className="page-note">
            研究进行中：你的问题正在被拆解，多名研究员并行检索资料并核对证据。
            下方是实时的研究进度（演示回放）。
          </p>
          {trace ? (
            <ResearchProgress events={trace} onDone={onProgressDone} />
          ) : (
            <p className="muted">正在准备研究环境…</p>
          )}
        </div>
      )}

      {phase === "report" && bundle && (
        <div className="step-panel">
          <div className="report-heading">
            <div>
              <h3>研究报告</h3>
              <p className="muted">研究问题：{activeQuestion}</p>
            </div>
            <span className="tag tag-demo">
              {activeCase.tag === "demo" ? "演示数据" : activeCase.tag === "real" ? "真实运行" : "合成示例"}
            </span>
          </div>
          <ReportViewer bundle={bundle} activeTab={reportTab} onTab={setReportTab} notice={notice} />

          <form className="follow-up" onSubmit={followUpSubmit}>
            <input
              className="follow-up-input"
              placeholder="还想深入研究什么？换个问题再问一次…"
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
            />
            <button className="btn-primary ask-submit" type="submit" disabled={!followUp.trim()}>
              <ArrowUp size={15} />
            </button>
          </form>
        </div>
      )}

      <div className="case-shelf">
        <BookOpen size={14} />
        <span className="muted">也可以直接查看示例报告：</span>
        {RUN_CASES.map((c) => (
          <button key={c.id} className="link-chip" onClick={() => submit(c.label)}>
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
