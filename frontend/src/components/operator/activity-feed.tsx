"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { StatusPill } from "@/components/operator/status-pill";
import { parseActivity, type ActivityItem, type ActivityProjection } from "@/lib/operator/types";

export function ActivityFeed({ initial }: { initial: ActivityProjection | null }) {
  const [projection, setProjection] = useState(initial);
  const [connection, setConnection] = useState<"connecting" | "live" | "polling" | "stale">("connecting");
  const [selected, setSelected] = useState<ActivityItem | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (selected && dialogRef.current && !dialogRef.current.open) {
      dialogRef.current.showModal();
      dialogRef.current.querySelector<HTMLButtonElement>("button")?.focus();
    }
  }, [selected]);

  const closeDetails = () => {
    setSelected(null);
    triggerRef.current?.focus();
  };

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/operator/activity", { cache: "no-store" });
      if (response.status === 401 || response.status === 403) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error("Activity request failed");
      const next = parseActivity(await response.json());
      if (!next) throw new Error("Invalid activity projection");
      setProjection(next);
      setConnection((current) => current === "live" ? current : "polling");
    } catch {
      setConnection("stale");
    }
  }, []);

  useEffect(() => {
    if (typeof EventSource === "undefined") {
      const first = window.setTimeout(() => void refresh(), 0);
      const timer = window.setInterval(() => void refresh(), 15_000);
      return () => { window.clearTimeout(first); window.clearInterval(timer); };
    }

    const source = new EventSource("/api/operator/activity/events");
    let timer: number | undefined;
    const handleUpdate = () => void refresh();
    source.addEventListener("snapshot", handleUpdate);
    source.addEventListener("update", handleUpdate);
    source.addEventListener("activity", handleUpdate);
    source.onmessage = handleUpdate;
    source.onopen = () => setConnection("live");
    source.onerror = () => {
      source.close();
      setConnection("polling");
      void refresh();
      if (timer === undefined) timer = window.setInterval(() => void refresh(), 15_000);
    };
    return () => {
      source.close();
      if (timer !== undefined) window.clearInterval(timer);
    };
  }, [refresh]);

  return (
    <section className="panel activity-panel" id="activity" aria-labelledby="activity-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Server activity</p>
          <h2 id="activity-heading">Activity log</h2>
        </div>
        <span className="connection-label" role="status">
          <span aria-hidden="true" className={`connection-light connection-light--${connection}`} />
          {connection === "live" ? "Live" : connection === "polling" ? "Polling" : connection === "stale" ? "Updates unavailable" : "Connecting"}
        </span>
      </div>

      {connection === "stale" && projection && (
        <div className="inline-notice" role="status">
          <StatusPill state="stale" /> Last confirmed activity is shown. <button type="button" onClick={() => void refresh()}>Retry</button>
        </div>
      )}

      {!projection ? (
        <div className="empty-state" role="status">
          <span className="empty-state__symbol" aria-hidden="true">○</span>
          <h3>Activity unavailable</h3>
          <p>The server has not supplied an activity projection. Try again when the connection recovers.</p>
          <button type="button" onClick={() => void refresh()}>Retry activity</button>
        </div>
      ) : projection.items.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state__symbol" aria-hidden="true">◇</span>
          <h3>No recorded activity</h3>
          <p>Server-confirmed work will appear here when an experiment starts.</p>
        </div>
      ) : (
        <ol className="activity-list">
          {projection.items.map((item) => (
            <li className="activity-item" key={item.id}>
              <div className="activity-item__line" aria-hidden="true" />
              <div className="activity-item__marker" aria-hidden="true" />
              <div className="activity-item__body">
                <div className="activity-item__top"><span className="activity-kind">{item.kind}</span><StatusPill state={item.state} /></div>
                <p>{item.label}</p>
                <time dateTime={item.occurred_at}>{formatUtc(item.occurred_at)}</time>
                <button className="activity-detail-trigger" type="button" aria-label={`View details for ${item.label}`} onClick={(event) => { triggerRef.current = event.currentTarget; setSelected(item); }}>View details <span aria-hidden="true">↗</span></button>
              </div>
            </li>
          ))}
        </ol>
      )}
      {selected && (
        <dialog ref={dialogRef} className="activity-drawer" aria-modal="true" aria-labelledby="activity-details-title" onCancel={(event) => { event.preventDefault(); closeDetails(); }} onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); closeDetails(); } }}>
          <div className="activity-drawer__heading"><div><p className="eyebrow">Server activity</p><h3 id="activity-details-title">Activity details</h3></div><button type="button" onClick={closeDetails} aria-label="Close details">Close <span aria-hidden="true">×</span></button></div>
          <p className="activity-drawer__label">{selected.label}</p>
          <dl className="activity-drawer__fields">
            <div><dt>State</dt><dd><StatusPill state={selected.state} /></dd></div>
            <div><dt>Kind</dt><dd>{selected.kind}</dd></div>
            <div><dt>Recorded at</dt><dd><time dateTime={selected.occurred_at}>{formatUtc(selected.occurred_at)}</time></dd></div>
            <div><dt>Activity ID</dt><dd>{selected.id}</dd></div>
          </dl>
        </dialog>
      )}
    </section>
  );
}

function formatUtc(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unknown";
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}
