import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { ReportViewer, type ReportTab } from "./ReportViewer";
import { liveReportToBundle, runLiveResearch, type LiveProgress, type LiveReport } from "../live/engine";

export function LiveResearch({ question }: { question: string }) {
  const [progress, setProgress] = useState<LiveProgress | null>(null);
  const [report, setReport] = useState<LiveReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportTab, setReportTab] = useState<ReportTab>("report");
  const reportTabRef = useRef<ReportTab>("report");
  const setReportTabSafe = (t: ReportTab) => {
    reportTabRef.current = t;
    setReportTab(t);
  };

  async function start() {
    if (running) return;
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const result = await runLiveResearch(question, setProgress);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    if (question.trim()) void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question]);

  const subStatus = progress?.subtopicStatus ?? {};

  return (
    <div className="live-research">
      <div className="honesty-banner">
        <strong>关于在线体验的说明：</strong>
        多 agent 系统以 LLM 为大脑——规划、检索决策、总结与审计都依赖模型。本在线页面未配置模型，
        因此下方执行的是<strong>多源检索工具</strong>（固定规则查询 + 摘录汇编），<strong>不是 agent 系统</strong>。
        完整的系统（多 agent 研究、证据审计、报告交付）在仓库中实现：内置真实 LLM agent 组合与
        受治理的联网检索（Tavily / GitHub / arXiv），配置模型凭据后即可复现（真实运行证据见
        `evals/reports/live_agent/`，详见 README）。
      </div>

      <div className="live-toolbar">
        <button className="mode-btn active" title="无 LLM：多源检索 + 摘录汇编（非 agent）">
          <Search size={14} /> 快速检索（免 Key，非 agent）
        </button>
        <span className="muted live-key-note">真实执行：浏览器直接检索 Wikipedia / OpenAlex / Crossref</span>
      </div>

      <div className="live-actions">
        <button className="btn-primary" onClick={start} disabled={running}>
          {running ? "检索中…" : report ? "重新检索" : "开始快速检索"}
        </button>
        <span className="muted">固定规则查询 → 并行抓取三个学术/百科数据源摘要</span>
      </div>

      {error && <div className="live-error">⚠ {error}</div>}

      {running && progress && (
        <div className="live-progress">
          <div className="live-phase">{progress.message}</div>
          <div className="live-subtopics">
            {(progress.plan?.subtopics ?? []).map((s) => {
              const st = subStatus[s.id] ?? "pending";
              return (
                <div className={`live-subtopic ${st}`} key={s.id}>
                  <span className="live-subtopic-icon">
                    {st === "done" ? "✓" : st === "searching" ? "…" : "·"}
                  </span>
                  <div>
                    <strong>{s.title}</strong>
                    <span className="muted">
                      {st === "done" ? "完成" : st === "searching" ? "检索中…" : "等待"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          {progress.sourceCount !== undefined && progress.sourceCount > 0 && (
            <div className="muted">已收集 {progress.sourceCount} 条真实来源</div>
          )}
        </div>
      )}

      {report && (
        <div className="step-panel live-report">
          <ReportViewer
            bundle={liveReportToBundle(report, question)}
            activeTab={reportTab}
            onTab={setReportTabSafe}
            notice={
              <>
                <strong>快速检索产物（非 agent）：</strong>未配置模型，本页仅执行多源检索与摘录汇编，
                不含任何 LLM 决策。完整的多 agent 研究（规划 → 并行研究 → 证据审计 → 报告）需要运行
                仓库中的系统，详见 README。
              </>
            }
          />
        </div>
      )}
    </div>
  );
}
