import { useEffect, useMemo, useRef, useState } from "react";
import { Play, Pause, RotateCcw, ChevronRight } from "lucide-react";
import { RUN_CASES, useTrace } from "../data";
import type { TraceEvent } from "../data/types";

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

export function TraceReplay({
  selectedRun,
  onSelectRun,
}: {
  selectedRun: string;
  onSelectRun: (id: string) => void;
}) {
  const active = RUN_CASES.find((c) => c.id === selectedRun) ?? RUN_CASES[0];
  const events = useTrace(active.tracePath);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(400);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [active.id]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setTimeout(() => {
      setIndex((i) => {
        if (events && i >= events.length - 1) {
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

  const stageCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const e of events ?? []) map.set(e.stage, (map.get(e.stage) ?? 0) + 1);
    return map;
  }, [events]);

  if (!events) {
    return (
      <div className="page">
        <h2>Multi-Agent Trace Replay</h2>
        <p className="muted">This run has no recorded trace.</p>
      </div>
    );
  }

  const current: TraceEvent | undefined = events[index];
  const visible = events.slice(0, index + 1);

  return (
    <div className="page">
      <h2>Multi-Agent Trace Replay</h2>
      <p className="page-note">
        Step through the recorded event journal of a research job: stage transitions, tool
        calls, claim extraction and audit decisions. This is <code>trace.jsonl</code> — a
        first-class runtime artifact.
      </p>

      <div className="run-selector">
        {RUN_CASES.map((c) => (
          <button
            key={c.id}
            className={`run-btn${c.id === selectedRun ? " active" : ""}`}
            onClick={() => onSelectRun(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="replay-controls">
        <button className="btn-small" onClick={() => setPlaying(!playing)}>
          {playing ? <Pause size={14} /> : <Play size={14} />} {playing ? "Pause" : "Play"}
        </button>
        <button className="btn-small" onClick={() => { setIndex(0); setPlaying(false); }}>
          <RotateCcw size={14} /> Restart
        </button>
        <input
          type="range"
          min={1}
          max={events.length}
          value={index + 1}
          onChange={(e) => { setIndex(Number(e.target.value) - 1); setPlaying(false); }}
          className="slider"
        />
        <span className="muted">
          event {index + 1} / {events.length}
        </span>
        <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="speed-select">
          <option value={800}>0.5×</option>
          <option value={400}>1×</option>
          <option value={150}>3×</option>
          <option value={60}>8×</option>
        </select>
      </div>

      <div className="stage-bar">
        {[...stageCounts.keys()].map((stage) => (
          <div key={stage} className="stage-chip" style={{ background: STAGE_COLORS[stage] ?? "#94a3b8" }}>
            {stage} ×{stageCounts.get(stage)}
          </div>
        ))}
      </div>

      {current && (
        <div className="current-event">
          <span className="event-stage" style={{ background: STAGE_COLORS[current.stage] ?? "#94a3b8" }}>
            {current.stage}
          </span>
          <code>{current.event_type}</code>
          <span className="muted">{current.timestamp}</span>
          <p>{current.message}</p>
          {Object.keys(current.payload ?? {}).length > 0 && (
            <pre className="event-payload">{JSON.stringify(current.payload, null, 1).slice(0, 800)}</pre>
          )}
        </div>
      )}

      <div className="event-timeline">
        {visible.map((e, i) => (
          <button
            key={e.event_id}
            className={`timeline-event${i === index ? " active" : ""}`}
            onClick={() => { setIndex(i); setPlaying(false); }}
          >
            <span className="tl-stage" style={{ background: STAGE_COLORS[e.stage] ?? "#94a3b8" }} />
            <span className="tl-seq">{e.sequence}</span>
            <span className="tl-type">{e.event_type}</span>
            <span className="tl-msg">{e.message}</span>
            <ChevronRight size={12} className="muted" />
          </button>
        ))}
      </div>
    </div>
  );
}
