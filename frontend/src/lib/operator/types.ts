import type { components } from "@/lib/api/schema";

export type ActivityItem = components["schemas"]["ActivityItem"];
export type ActivityState = ActivityItem["state"];

export type ActivityProjection = components["schemas"]["ActivityResponse"];

export type StatusProjection = components["schemas"]["SystemStatus"] & {
  health: { status: "ok" };
  readiness: { status: "ready" | "not_ready" };
  counts: Record<ActivityState, number>;
};

const states = new Set<ActivityState>(["queued", "running", "completed", "blocked"]);

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseActivity(value: unknown): ActivityProjection | null {
  if (!record(value) || !Array.isArray(value.items)) return null;
  const items: ActivityItem[] = [];
  for (const item of value.items) {
    if (
      !record(item) || typeof item.id !== "string" ||
      typeof item.kind !== "string" || typeof item.label !== "string" ||
      typeof item.occurred_at !== "string" ||
      !states.has(item.state as ActivityState)
    ) return null;
    items.push(item as ActivityItem);
  }
  if (value.cursor !== null && typeof value.cursor !== "string") return null;
  return { items, cursor: value.cursor as string | null };
}

export function parseStatus(value: unknown): StatusProjection | null {
  if (!record(value) || !record(value.health) || !record(value.readiness) || !record(value.counts)) return null;
  if (value.health.status !== "ok" || !["ready", "not_ready"].includes(String(value.readiness.status))) return null;
  for (const state of states) {
    const count = value.counts[state];
    if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) return null;
  }
  return value as StatusProjection;
}
