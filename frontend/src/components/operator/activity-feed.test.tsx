import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ActivityFeed } from "@/components/operator/activity-feed";
import type { ActivityProjection } from "@/lib/operator/types";

class TestEventSource {
  static current: TestEventSource;
  listeners = new Map<string, () => void>();
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  close = vi.fn();
  addEventListener = vi.fn((name: string, listener: () => void) => { this.listeners.set(name, listener); });
  constructor() { TestEventSource.current = this; }
  emit(name: string) { this.listeners.get(name)?.(); }
}

beforeEach(() => { vi.stubGlobal("EventSource", TestEventSource); });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal"); });

describe("ActivityFeed", () => {
  it("keeps the unknown state explicit when the projection is absent", () => {
    render(<ActivityFeed initial={null} />);
    expect(screen.getByText("Activity unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Completed")).not.toBeInTheDocument();
  });

  it("renders each authoritative state without implying progress", () => {
    const projection: ActivityProjection = {
      cursor: null,
      items: (["queued", "running", "completed", "blocked"] as const).map((state) => ({
        id: state, kind: "research", state, label: `${state} work`, occurred_at: "2026-09-23T10:00:00Z",
      })),
    };
    render(<ActivityFeed initial={projection} />);
    for (const state of ["Queued", "Running", "Completed", "Blocked"]) expect(screen.getByText(state)).toBeInTheDocument();
    expect(screen.getAllByText("2026-09-23 10:00 UTC")).toHaveLength(4);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("falls back to polling after the live stream fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], cursor: null }) }));
    render(<ActivityFeed initial={null} />);
    TestEventSource.current.onerror?.();
    await waitFor(() => expect(screen.getByText("No recorded activity")).toBeInTheDocument());
    expect(screen.getByText("Polling")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/operator/activity", { cache: "no-store" });
  });

  it("refreshes the projection when the backend emits a named activity event", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [{ id: "1", kind: "research", state: "completed", label: "Research completed", occurred_at: "2026-09-23T10:00:00Z" }], cursor: null }) }));
    render(<ActivityFeed initial={{ items: [], cursor: null }} />);
    TestEventSource.current.emit("activity");
    await waitFor(() => expect(screen.getByText("Research completed")).toBeInTheDocument());
    expect(fetch).toHaveBeenCalledWith("/api/operator/activity", { cache: "no-store" });
  });

  it("opens a keyboard-accessible read-only drawer with sanitized activity fields", () => {
    const trigger = "Research completed";
    const showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value: showModal });
    render(<ActivityFeed initial={{ cursor: null, items: [{ id: "item-1", kind: "research", state: "completed", label: trigger, occurred_at: "2026-09-23T10:00:00Z", evidence_text: "private evidence" }] } as unknown as ActivityProjection} />);
    const button = screen.getByRole("button", { name: /view details for research completed/i });
    button.focus();
    fireEvent.click(button);

    const drawer = screen.getByRole("dialog", { name: "Activity details" });
    expect(showModal).toHaveBeenCalledOnce();
    expect(drawer).toHaveAttribute("aria-modal", "true");
    expect(within(drawer).getByText(trigger)).toBeInTheDocument();
    expect(within(drawer).getByText("item-1")).toBeInTheDocument();
    expect(within(drawer).getByText("2026-09-23 10:00 UTC")).toBeInTheDocument();
    expect(within(drawer).queryByRole("textbox")).not.toBeInTheDocument();
    expect(within(drawer).queryByText("private evidence")).not.toBeInTheDocument();
    expect(within(drawer).getByRole("button", { name: "Close details" })).toHaveFocus();

    fireEvent.keyDown(drawer, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });
});
