import { useEffect, useMemo, useRef, useState } from "react";
import { Play, Pause, RotateCcw, Check } from "lucide-react";
import type { TraceEvent } from "../data/types";

const STAGE_ORDER = [
  "job",
  "clarifying",
  "planned",
  "collecting",
  "normalizing",
  "extracting",
  "claim_auditing",
  "synthesizing",
  "rendering",
  "completed",
];

const STAGE_LABELS: Record<string, string> = {
  job: "创建任务",
  clarifying: "理解问题",
  planned: "规划研究",
  collecting: "并行检索",
  normalizing: "整理资料",
  extracting: "提取要点",
  claim_auditing: "核对证据",
  synthesizing: "撰写报告",
  rendering: "排版生成",
  completed: "完成",
};

const STAGE_COLORS: Record<string, string> = {
  job: "#94a3b8",
  clarifying: "#f59e0b",
  planned: "#3b82f6",
  collecting: "#8b5cf6",
  normalizing: "#0ea5e9",
  extracting: "#10b981",
  claim_auditing: "#ef4444",
  synthesizing: "#f97316",
  rendering: "#64748b",
  completed: "#22c55e",
};

function laneKey(event: TraceEvent): string {
  const taskId = event.payload?.task_id;
  if (typeof taskId === "string" && (taskId.startsWith("research") || taskId.startsWith("critic"))) {
    return taskId;
  }
  if (event.stage === "planned") return "planner";
  return "system";
}

function isDone(event: TraceEvent): boolean {
  return event.event_type.includes("completed");
}

function isStarted(event: TraceEvent): boolean {
  return event.event_type.includes("started") || event.event_type === "task.spawned";
}

interface LaneDef {
  id: string;
  title: string;
  subtitle: string;
  role: string;
}

const LANE_DEFS: LaneDef[] = [
  { id: "planner", title: "研究规划", subtitle: "拆解问题、安排任务", role: "规划" },
  { id: "research-1", title: "研究员 1", subtitle: "产品线与商业模式", role: "研究员" },
  { id: "research-2", title: "研究员 2", subtitle: "融资历程与估值", role: "研究员" },
  { id: "research-3", title: "研究员 3", subtitle: "研发实践与行业影响", role: "研究员" },
  { id: "critic-1", title: "证据核对", subtitle: "逐条核对结论出处", role: "核对" },
  { id: "system", title: "研究流程", subtitle: "阶段推进与任务编排", role: "流程" },
];

export function ResearchProgress({ events, onDone }: { events: TraceEvent[]; onDone: () => void }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIndex(0);
    setPlaying(true);
  }, [events]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setTimeout(() => {
      setIndex((i) => {
        if (i >= events.length - 1) {
          setPlaying(false);
          onDone();
          return i;
        }
        return i + 1;
      });
    }, 260);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [playing, index, events, onDone]);

  const visible = events.slice(0, index + 1);
  const current = visible[visible.length - 1];
  const currentStage = current?.stage ?? "job";
  const stageIndex = Math.max(0, STAGE_ORDER.indexOf(currentStage));

  const lanes = useMemo(() => {
    return LANE_DEFS.map((def) => {
      const laneEvents = events.filter((e) => laneKey(e) === def.id);
      const started = laneEvents.some(isStarted);
      const done = laneEvents.some(isDone);
      const activeEvents = laneEvents.filter((e) => visible.includes(e));
      return { ...def, events: activeEvents, started, done };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, index]);

  const progressPct = Math.round(((index + 1) / events.length) * 100);

  return (
    <div className="research-progress">
      <div className="progress-summary">
        <div className="stage-progress">
          {STAGE_ORDER.map((stage, i) => (
            <div
              key={stage}
              className={`stage-seg${i <= stageIndex ? " done" : ""}${stage === currentStage ? " current" : ""}`}
              style={{ background: i <= stageIndex ? STAGE_COLORS[stage] : undefined }}
            >
              <span className="stage-seg-label">{STAGE_LABELS[stage]}</span>
            </div>
          ))}
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <div className="replay-controls">
          <button className="btn-small" onClick={() => setPlaying(!playing)}>
            {playing ? <Pause size={14} /> : <Play size={14} />}
            {playing ? "暂停" : "继续"}
          </button>
          <button
            className="btn-small"
            onClick={() => {
              setIndex(0);
              setPlaying(true);
            }}
          >
            <RotateCcw size={14} /> 重看
          </button>
          <span className="muted">研究进度 {progressPct}%</span>
        </div>
      </div>

      <div className="lanes">
        {lanes.map((lane) => {
          const isActive = lane.events.length > 0 && !lane.done;
          return (
            <div className={`lane ${isActive ? "active" : ""}`} key={lane.id}>
              <div className="lane-head">
                <span className="lane-role">{lane.role}</span>
                <strong>{lane.title}</strong>
                <span className="muted">{lane.subtitle}</span>
                <span className={`lane-status ${lane.done ? "done" : lane.started ? "running" : ""}`}>
                  {lane.done ? (
                    <>
                      <Check size={13} /> 完成
                    </>
                  ) : lane.started ? (
                    "工作中…"
                  ) : (
                    "等待"
                  )}
                </span>
              </div>
              <div className="lane-events">
                {lane.events.slice(-3).map((e) => (
                  <div className="lane-event" key={e.event_id}>
                    <span className="muted">{e.message}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="current-event">
        {current && (
          <>
            <span className="event-stage" style={{ background: STAGE_COLORS[current.stage] ?? "#94a3b8" }}>
              {STAGE_LABELS[current.stage] ?? current.stage}
            </span>
            <p>{current.message}</p>
          </>
        )}
      </div>
    </div>
  );
}
