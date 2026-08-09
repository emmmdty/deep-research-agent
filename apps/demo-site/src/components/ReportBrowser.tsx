import { useState } from "react";
import { ReportViewer, type ReportTab } from "./ReportViewer";
import { RUN_CASES, useBundle } from "../data";

const TAG_LABEL: Record<string, string> = {
  demo: "演示数据",
  real: "真实运行",
  fixture: "评测样本",
  sample: "合成样本",
};

export function ReportBrowser() {
  const [selectedRun, setSelectedRun] = useState(RUN_CASES[0].id);
  const [tab, setTab] = useState<ReportTab>("report");

  const active = RUN_CASES.find((c) => c.id === selectedRun) ?? RUN_CASES[0];
  const bundle = useBundle(active.bundlePath);

  return (
    <div className="page">
      <h2>报告与证据</h2>
      <p className="page-note">
        案例库中的每一份报告都保留了完整的执行轨迹、结论清单、证据链与审计记录。选择案例查看。
      </p>

      <div className="run-selector">
        {RUN_CASES.map((c) => (
          <button
            key={c.id}
            className={`run-btn${c.id === selectedRun ? " active" : ""}${c.highlight ? " highlight" : ""}`}
            onClick={() => {
              setSelectedRun(c.id);
              setTab("report");
            }}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="run-meta">
        <span className={`tag ${active.tag === "demo" ? "tag-demo" : active.tag === "real" ? "tag-real" : ""}`}>
          {TAG_LABEL[active.tag]}
        </span>
        <code>{bundle?.job.job_id ?? "…"}</code>
        <span className="muted">来源策略：{bundle?.job.source_profile ?? "…"}</span>
        <span className="muted">运行时：{bundle?.job.runtime_path ?? "…"}</span>
      </div>
      <p className="run-desc">{active.description}</p>

      {bundle ? (
        <ReportViewer bundle={bundle} activeTab={tab} onTab={setTab} />
      ) : (
        <p className="muted">加载中…</p>
      )}
    </div>
  );
}
