import { Radio } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { productApi } from "../../api/client";
import type { ProductRun, ReportBundle, RunEvent } from "../../types";

type ConnectionState = "live" | "reconnecting" | "recovered";

function workerRows(bundle: ReportBundle) {
  const manifest = bundle.run_manifest ?? {};
  const raw = Array.isArray(manifest.tasks) ? manifest.tasks : Array.isArray(manifest.workers) ? manifest.workers : [];
  return raw.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"));
}

export function RunConnectionBadge({ runId }: { runId: string }) {
  const [connection, setConnection] = useState<ConnectionState>("live");

  useEffect(() => {
    const onTestError = () => setConnection("reconnecting");
    const onTestEvent = (event: Event) => {
      setConnection("recovered");
      void (event as CustomEvent<RunEvent>).detail;
    };
    window.addEventListener("dra:test-stream-error", onTestError);
    window.addEventListener("dra:test-stream-event", onTestEvent);
    let source: EventSource | null = null;
    if (typeof EventSource !== "undefined") {
      source = new EventSource(productApi.productEventUrl(runId), { withCredentials: true });
      source.onopen = () => setConnection((current) => current === "reconnecting" ? "recovered" : "live");
      source.onerror = () => setConnection("reconnecting");
      source.onmessage = (event) => {
        try {
          JSON.parse(event.data) as RunEvent;
          setConnection("recovered");
        } catch { /* malformed progress events are ignored */ }
      };
    }
    return () => {
      source?.close();
      window.removeEventListener("dra:test-stream-error", onTestError);
      window.removeEventListener("dra:test-stream-event", onTestEvent);
    };
  }, [runId]);

  const connectionLabel = connection === "live" ? "实时连接" : connection === "reconnecting" ? "正在重新连接" : "已恢复连接";
  return <div className={`connection-state ${connection}`}><Radio size={14} />{connectionLabel}</div>;
}

export function RunTelemetry({ run, bundle }: { run: ProductRun; bundle: ReportBundle }) {
  const workers = useMemo(() => workerRows(bundle), [bundle]);
  const fallbackWorker: Record<string, unknown> = { task: run.question, role: "research coordinator", model: run.config_version_id, state: run.status, retry: "0", source_count: "-", elapsed: "-" };
  const displayWorkers: Record<string, unknown>[] = workers.length ? workers : [fallbackWorker];

  return (
    <div className="run-telemetry">
      <div className="worker-table" role="table" aria-label="Agent 工作状态">
        <div className="worker-row worker-head" role="row"><span>任务</span><span>角色</span><span>模型</span><span>状态</span><span>重试</span><span>来源</span><span>耗时</span></div>
        {displayWorkers.map((worker, index) => (
          <div className="worker-row" role="row" key={String(worker.task_id ?? worker.task ?? index)}>
            <span>{String(worker.task_id ?? worker.task ?? "task")}</span>
            <span>{String(worker.role ?? "researcher")}</span>
            <span className="monospace">{String(worker.model ?? worker.model_id ?? "default")}</span>
            <span><i className={`worker-state ${String(worker.state ?? worker.status ?? "queued")}`} />{String(worker.state ?? worker.status ?? "queued")}</span>
            <span>{String(worker.retry ?? worker.retry_count ?? 0)}</span>
            <span>{String(worker.source_count ?? 0)}</span>
            <span>{String(worker.elapsed ?? worker.elapsed_seconds ?? "-")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
