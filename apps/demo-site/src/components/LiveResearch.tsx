import { useEffect, useRef, useState } from "react";
import { Globe, KeyRound, Trash2 } from "lucide-react";
import { ReportViewer, type ReportTab } from "./ReportViewer";
import { runLiveResearch, type LiveProgress, type LiveReport } from "../live/engine";
import type { LlmConfig } from "../live/llm";
import { clearLlmConfig, loadLlmConfig, saveLlmConfig } from "../live/llm";
import { liveReportToBundle } from "../live/engine";

const LLM_PRESETS = [
  { label: "DeepSeek", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { label: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  { label: "Moonshot", baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
  { label: "自定义", baseUrl: "", model: "" },
];

export function LiveResearch({ question }: { question: string }) {
  const [progress, setProgress] = useState<LiveProgress | null>(null);
  const [report, setReport] = useState<LiveReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showKeyPanel, setShowKeyPanel] = useState(false);
  const [llm, setLlm] = useState<LlmConfig | null>(() => loadLlmConfig());
  const [baseUrl, setBaseUrl] = useState(loadLlmConfig()?.baseUrl ?? LLM_PRESETS[0].baseUrl);
  const [apiKey, setApiKey] = useState(loadLlmConfig()?.apiKey ?? "");
  const [model, setModel] = useState(loadLlmConfig()?.model ?? LLM_PRESETS[0].model);
  const [preset, setPreset] = useState(LLM_PRESETS[0].label);
  const reportTabRef = useRef<ReportTab>("report");

  const [reportTab, setReportTabState] = useState<ReportTab>("report");
  const setReportTab = (t: ReportTab) => {
    reportTabRef.current = t;
    setReportTabState(t);
  };

  useEffect(() => {
    if (question.trim()) void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question]);

  async function start() {
    if (running) return;
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const result = await runLiveResearch(question, llm, setProgress);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  function applyPreset(label: string) {
    setPreset(label);
    const p = LLM_PRESETS.find((x) => x.label === label)!;
    setBaseUrl(p.baseUrl);
    setModel(p.model);
  }

  function saveKey() {
    if (!baseUrl.trim() || !apiKey.trim() || !model.trim()) {
      setError("请填写完整的 Base URL、API Key 与模型名");
      return;
    }
    const config = { baseUrl: baseUrl.trim(), apiKey: apiKey.trim(), model: model.trim() };
    saveLlmConfig(config);
    setLlm(config);
    setShowKeyPanel(false);
    setError(null);
  }

  function removeKey() {
    clearLlmConfig();
    setLlm(null);
    setApiKey("");
    setError(null);
  }

  const subStatus = progress?.subtopicStatus ?? {};

  return (
    <div className="live-research">
      <div className="live-toolbar">
        <button
          className={`mode-btn${llm ? "" : " active"}`}
          onClick={() => setShowKeyPanel(false)}
          title="免 Key：浏览器直接检索公开学术/百科数据源"
        >
          <Globe size={14} /> 免 Key 模式
        </button>
        <button
          className={`mode-btn${llm ? " active" : ""}`}
          onClick={() => setShowKeyPanel(!showKeyPanel)}
          title="使用你自己的 OpenAI 兼容模型生成完整报告"
        >
          <KeyRound size={14} /> {llm ? `已配置 ${llm.model}` : "配置模型（可选）"}
        </button>
        <span className="muted live-key-note">
          {llm ? "已配置模型，将生成完整报告" : "未配置模型：真实检索 + 摘录汇编"}
        </span>
      </div>

      {showKeyPanel && (
        <div className="key-panel">
          <div className="key-row">
            <label>服务商</label>
            <select value={preset} onChange={(e) => applyPreset(e.target.value)}>
              {LLM_PRESETS.map((p) => (
                <option key={p.label} value={p.label}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div className="key-row">
            <label>Base URL</label>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com/v1" />
          </div>
          <div className="key-row">
            <label>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-…"
            />
          </div>
          <div className="key-row">
            <label>模型名</label>
            <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="deepseek-chat" />
          </div>
          <div className="key-actions">
            <button className="btn-small" onClick={saveKey}>保存并使用</button>
            {llm && (
              <button className="btn-small" onClick={removeKey}>
                <Trash2 size={13} /> 清除
              </button>
            )}
          </div>
          <p className="muted key-note">
            Key 仅保存在你的浏览器本地（localStorage），只用于直接调用你选择的模型接口，不会上传到任何服务器。
          </p>
        </div>
      )}

      <div className="live-actions">
        <button className="btn-primary" onClick={start} disabled={running}>
          {running ? "研究进行中…" : report ? "重新研究" : "开始实时研究"}
        </button>
        <span className="muted">
          真实执行：浏览器直接检索 Wikipedia / OpenAlex / Crossref（免 Key）
        </span>
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
                      {st === "done" ? "检索完成" : st === "searching" ? "正在并行检索…" : "等待中"}
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
            onTab={setReportTab}
            notice={
              report.usedLlm ? (
                <>
                  <strong>实时研究产物：</strong>浏览器真实检索（Wikipedia / OpenAlex / Crossref）
                  + 你配置的模型生成。引用可点击核验。
                </>
              ) : (
                <>
                  <strong>实时研究产物（免 Key 模式）：</strong>浏览器直接检索公开学术/百科数据源，
                  未使用大模型。所有摘录与来源均为真实检索结果，可点击核验。
                </>
              )
            }
          />
        </div>
      )}
    </div>
  );
}
