import { useEffect, useMemo, useRef, useState } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
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
  clarifying: "澄清意图",
  planned: "规划任务",
  collecting: "并行研究",
  normalizing: "证据归并",
  extracting: "提取结论",
  claim_auditing: "证据审计",
  synthesizing: "撰写报告",
  rendering: "渲染交付",
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

function taskIdOf(event: TraceEvent): string | null {
  const taskId = event.payload?.task_id;
  if (typeof taskId === "string") return taskId;
  return null;
}

function roleOf(taskId: string | null): "planner" | "researcher" | "critic" | "system" {
  if (!taskId) return "system";
  if (taskId.startsWith("research")) return "researcher";
  if (taskId.startsWith("critic")) return "critic";
  return "planner";
}

interface Lane {
  id: string;
  title: string;
  subtitle: string;
  role: "planner" | "researcher" | "critic" | "system";
  events: TraceEvent[];
}

export function AgentProcess({ events }: { events: TraceEvent[] }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(350);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [events]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setTimeout(() => {
      setIndex((i) => {
        if (i >= events.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, speed);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [playing, index, speed, events]);

  const lanes = useMemo<Lane[]>(() => {
    const groups = new Map<string, TraceEvent[]>();
    for (const event of events) {
      const taskId = taskIdOf(event);
      let key: string;
      if (taskId && roleOf(taskId) !== "system") {
        key = taskId;
      } else if (event.stage === "planned") {
        key = "planner";
      } else {
        key = "system";
      }
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(event);
    }
    const laneDefs: Array<{ id: string; title: string; subtitle: string; role: Lane["role"]; order: number }> = [
      { id: "planner", title: "规划器 Planner", subtitle: "把问题拆解为任务图", role: "planner", order: 0 },
      { id: "research-1", title: "研究员 #1", subtitle: "产品线与商业模式", role: "researcher", order: 1 },
      { id: "research-2", title: "研究员 #2", subtitle: "融资历程与估值", role: "researcher", order: 2 },
      { id: "research-3", title: "研究员 #3", subtitle: "研发实践与行业影响", role: "researcher", order: 3 },
      { id: "critic-1", title: "审稿人 Critic", subtitle: "逐条审计证据", role: "critic", order: 4 },
      { id: "system", title: "系统", subtitle: "事件与阶段流转", role: "system", order: 5 },
    ];
    return laneDefs
      .map((def) => ({ ...def, events: groups.get(def.id) ?? [] }))
      .sort((a, b) => a.order - b.order);
  }, [events]);

  const visible = events.slice(0, index + 1);
  const currentStage = visible.length > 0 ? visible[visible.length - 1].stage : "job";
  const stageIndex = Math.max(0, STAGE_ORDER.indexOf(currentStage));

  return (
    <div className="agent-process">
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

      <div className="replay-controls">
        <button className="btn-small" onClick={() => setPlaying(!playing)}>
          {playing ? <Pause size={14} /> : <Play size={14} />}
          {playing ? "暂停" : "播放"}
        </button>
        <button className="btn-small" onClick={() => { setIndex(0); setPlaying(false); }}>
          <RotateCcw size={14} /> 重放
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, events.length - 1)}
          value={index}
          onChange={(e) => { setIndex(Number(e.target.value)); setPlaying(false); }}
          className="slider"
        />
        <span className="muted">
          事件 {index + 1} / {events.length}
        </span>
        <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="speed-select">
          <option value={700}>慢速</option>
          <option value={350}>正常</option>
          <option value={120}>快速</option>
        </select>
      </div>

      <div className="lanes">
        {lanes.map((lane) => {
          const laneVisible = lane.events.filter((e) => visible.includes(e));
          const started = laneVisible.some((e) => e.event_type.includes("started") || e.event_type === "task.spawned");
          const done = laneVisible.some((e) => e.event_type.includes("completed"));
          const isActive = laneVisible.length > 0 && !done;
          return (
            <div className={`lane ${isActive ? "active" : ""}`} key={lane.id}>
              <div className="lane-head">
                <span className={`lane-role role-${lane.role}`}>{lane.role}</span>
                <strong>{lane.title}</strong>
                <span className="muted">{lane.subtitle}</span>
                <span className={`lane-status ${done ? "done" : started ? "running" : ""}`}>
                  {done ? "✓ 完成" : started ? "工作中…" : lane.role === "system" ? "—" : "等待"}
                </span>
              </div>
              <div className="lane-events">
                {laneVisible.slice(-4).map((e) => (
                  <div className="lane-event" key={e.event_id}>
                    <span className="lane-event-type">{e.event_type}</span>
                    <span className="muted">{e.message}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="current-event">
        {visible.length > 0 && (
          <>
            <span className="event-stage" style={{ background: STAGE_COLORS[visible[visible.length - 1].stage] ?? "#94a3b8" }}>
              {STAGE_LABELS[visible[visible.length - 1].stage] ?? visible[visible.length - 1].stage}
            </span>
            <code>{visible[visible.length - 1].event_type}</code>
            <span className="muted">{visible[visible.length - 1].timestamp}</span>
            <p>{visible[visible.length - 1].message}</p>
          </>
        )}
      </div>
    </div>
  );
}
