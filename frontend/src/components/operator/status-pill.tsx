import type { ActivityState } from "@/lib/operator/types";

type Tone = ActivityState | "ready" | "not_ready" | "unknown" | "stale";

const labels: Record<Tone, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  blocked: "Blocked",
  ready: "Ready",
  not_ready: "Not ready",
  unknown: "Unknown",
  stale: "Stale",
};

export function StatusPill({ state, label }: { state: Tone; label?: string }) {
  return (
    <span className={`status-pill status-pill--${state}`}>
      <span className="status-pill__dot" aria-hidden="true" />
      {label ?? labels[state]}
    </span>
  );
}
