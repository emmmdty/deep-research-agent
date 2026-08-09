import { useEffect, useState } from "react";
import type { ReportBundle, TraceEvent } from "./types";

export function useBundle(path: string): ReportBundle | null {
  const [bundle, setBundle] = useState<ReportBundle | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch(path)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setBundle(d);
      })
      .catch(() => {
        if (!cancelled) setBundle(null);
      });
    return () => {
      cancelled = true;
    };
  }, [path]);
  return bundle;
}

export function useTrace(path?: string): TraceEvent[] | null {
  const [events, setEvents] = useState<TraceEvent[] | null>(null);
  useEffect(() => {
    if (!path) {
      setEvents(null);
      return;
    }
    let cancelled = false;
    fetch(path)
      .then((r) => r.text())
      .then((text) => {
        if (cancelled) return;
        const events = text
          .split("\n")
          .filter((line) => line.trim())
          .map((line) => JSON.parse(line) as TraceEvent)
          .sort((a, b) => a.sequence - b.sequence);
        setEvents(events);
      })
      .catch(() => {
        if (!cancelled) setEvents(null);
      });
    return () => {
      cancelled = true;
    };
  }, [path]);
  return events;
}

export async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`failed to load ${path}`);
  return response.json() as Promise<T>;
}
