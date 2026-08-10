import { useMemo, useRef, useState } from "react";
import { ArrowUp, PlayCircle, Radio } from "lucide-react";
import { LiveResearch } from "./LiveResearch";
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

type Mode = "live" | "replay";

export function ResearchPage({ question }: { question: string }) {
  const [input, setInput] = useState(question);
  const [activeQuestion, setActiveQuestion] = useState(question);
  const [mode, setMode] = useState<Mode>("live");
  const [replayTab, setReplayTab] = useState<ReportTab>("report");
  const [followUp, setFollowUp] = useState("");
  const [replayDone, setReplayDone] = useState(false);
  const replayDoneRef = useRef(false);

  const activeCase = useMemo(() => matchCase(activeQuestion), [activeQuestion]);
  const bundle = useBundle(activeCase.bundlePath);
  const trace = useTrace(activeCase.tracePath);

  function submit(text: string) {
    if (!text.trim()) return;
    setActiveQuestion(text.trim());
    setInput(text.trim());
    setMode("live");
    setReplayDone(false);
    replayDoneRef.current = false;
    window.scrollTo({ top: 0 });
  }

  function onReplayDone() {
    replayDoneRef.current = true;
    setReplayDone(true);
  }

  function followUpSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(followUp);
    setFollowUp("");
  }

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

      <div className="mode-tabs">
        <button className={`mode-tab${mode === "live" ? " active" : ""}`} onClick={() => setMode("live")}>
          <Radio size={14} /> 在线执行
        </button>
        <button className={`mode-tab${mode === "replay" ? " active" : ""}`} onClick={() => setMode("replay")}>
          <PlayCircle size={14} /> 演示回放（内建案例）
        </button>
      </div>

      {mode === "live" && <LiveResearch key={activeQuestion} question={activeQuestion} />}

      {mode === "replay" && (
        <div className="step-panel">
          <p className="page-note">
            演示回放展示系统内建的研究案例（确定性演示数据，基于 2025 年公开信息整理）。
            实时研究模式则会真实检索网络数据源。
          </p>
          {trace ? (
            <ResearchProgress events={trace} onDone={onReplayDone} />
          ) : (
            <p className="muted">正在准备…</p>
          )}
          {replayDone && bundle && (
            <div className="replay-report">
              <h3>报告（演示数据）</h3>
              <ReportViewer
                bundle={bundle}
                activeTab={replayTab}
                onTab={setReplayTab}
                notice={
                  <>
                    <strong>演示数据：</strong>此报告为确定性生成的演示案例，用于展示完整的产品形态。
                  </>
                }
              />
            </div>
          )}
        </div>
      )}

      <form className="follow-up" onSubmit={followUpSubmit}>
        <input
          className="follow-up-input"
          placeholder="还想研究什么？换个问题再试一次…"
          value={followUp}
          onChange={(e) => setFollowUp(e.target.value)}
        />
        <button className="btn-primary ask-submit" type="submit" disabled={!followUp.trim()}>
          <ArrowUp size={15} />
        </button>
      </form>

      <div className="case-shelf">
        <span className="muted">直接体验预设问题：</span>
        {[
          "研究 Anthropic 公司的产品线、商业模式与融资历程",
          "研究同花顺这家公司的基本面和业务",
          "DeepSeek-V4 的架构有哪些关键技术？",
        ].map((q) => (
          <button key={q} className="link-chip" onClick={() => submit(q)}>
            {q.slice(0, 24)}…
          </button>
        ))}
      </div>
    </div>
  );
}
