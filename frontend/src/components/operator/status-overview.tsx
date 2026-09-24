"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";

import { StatusPill } from "@/components/operator/status-pill";
import { parseStatus, type ActivityState, type StatusProjection } from "@/lib/operator/types";

const ActivitySignal = dynamic(() => import("./activity-signal").then((module) => module.ActivitySignal), {
  ssr: false,
  loading: () => <div className="signal-fallback" aria-hidden="true" />,
});

const sequence: ActivityState[] = ["queued", "running", "completed", "blocked"];

export function StatusOverview({ initial }: { initial: StatusProjection | null }) {
  const [projection, setProjection] = useState(initial);
  const [stale, setStale] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/operator/status", { cache: "no-store" });
      if (response.status === 401 || response.status === 403) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error("Status request failed");
      const next = parseStatus(await response.json());
      if (!next) throw new Error("Invalid status projection");
      setProjection(next);
      setStale(false);
    } catch {
      setStale(true);
    }
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const current = stale ? null : projection;

  return (
    <section className="panel system-panel" id="system" aria-labelledby="system-heading">
      <div className="panel-heading">
        <div><p className="eyebrow">Source · operator API</p><h2 id="system-heading">System status</h2></div>
        <button className="text-button" type="button" onClick={() => void refresh()}>Refresh <span aria-hidden="true">↗</span></button>
      </div>
      {stale && <div className="inline-notice" role="status"><StatusPill state="stale" /> Status could not be refreshed.</div>}
      <div className="system-state-grid">
        <div className="system-state"><span>API health</span><StatusPill state={current?.health.status === "ok" ? "ready" : "unknown"} label={current?.health.status === "ok" ? "Online" : "Unknown"} /></div>
        <div className="system-state"><span>Readiness</span><StatusPill state={current?.readiness.status ?? "unknown"} /></div>
      </div>
      <div className="workload-heading"><span>Recorded work</span><span>{current ? "Current projection" : "Projection unavailable"}</span></div>
      <div className="workload-content">
        <div className="workload-grid" aria-label="Activity counts">
          {sequence.map((state) => <div className="workload-cell" key={state}><span>{state}</span><strong>{current ? current.counts[state] : "—"}</strong></div>)}
        </div>
        {current && <ActivitySignal counts={current.counts} />}
      </div>
      {!current && <p className="status-explanation">No current status projection is available. Counts remain unknown until the server responds.</p>}
    </section>
  );
}
