import type { ActivityState } from "@/lib/operator/types";

const order: ActivityState[] = ["queued", "running", "completed", "blocked"];

export function ActivitySignal({ counts }: { counts: Record<ActivityState, number> }) {
  const max = Math.max(1, ...order.map((state) => counts[state]));
  return (
    <div className="activity-signal" aria-hidden="true">
      {order.map((state) => (
        <span key={state} className={`activity-signal__bar activity-signal__bar--${state}`} style={{ height: `${counts[state] === 0 ? 0 : Math.max(7, counts[state] / max * 100)}%` }} />
      ))}
    </div>
  );
}
