import { describe, expect, it } from "vitest";

import { parseActivity, parseStatus } from "@/lib/operator/types";

describe("operator projections", () => {
  it("accepts only server-defined activity states", () => {
    const item = { id: "run-1", kind: "research", state: "running", label: "Research is running", occurred_at: "2026-09-23T10:00:00Z" };
    expect(parseActivity({ items: [item], cursor: null })?.items[0].state).toBe("running");
    expect(parseActivity({ items: [{ ...item, state: "successful" }], cursor: null })).toBeNull();
    expect(parseActivity({ items: [{ ...item, label: 42 }], cursor: null })).toBeNull();
  });

  it("refuses an incomplete status rather than inventing counts", () => {
    const valid = { health: { status: "ok" }, readiness: { status: "ready" }, counts: { queued: 0, running: 1, completed: 2, blocked: 0 } };
    expect(parseStatus(valid)?.counts.running).toBe(1);
    expect(parseStatus({ ...valid, counts: { queued: 0, running: 1 } })).toBeNull();
    expect(parseStatus({ ...valid, counts: { ...valid.counts, blocked: -1 } })).toBeNull();
  });
});
