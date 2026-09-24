import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StatusOverview } from "@/components/operator/status-overview";
import type { StatusProjection } from "@/lib/operator/types";

vi.mock("next/dynamic", () => ({
  default: () => function TestSignal() { return <div data-testid="activity-signal" />; },
}));

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("StatusOverview", () => {
  it("stops presenting confirmed values as current after refresh fails", async () => {
    const initial = {
      health: { status: "ok" }, readiness: { status: "ready" },
      counts: { queued: 1, running: 2, completed: 3, blocked: 4 },
    } as StatusProjection;
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    render(<StatusOverview initial={initial} />);
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Current projection")).toBeInTheDocument();
    expect(screen.getByTestId("activity-signal")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => expect(screen.getByText("Status could not be refreshed.")).toBeInTheDocument());

    expect(screen.queryByText("Online")).not.toBeInTheDocument();
    expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    expect(screen.queryByText("Current projection")).not.toBeInTheDocument();
    expect(screen.getAllByText("Unknown")).toHaveLength(2);
    expect(screen.getAllByText("—")).toHaveLength(4);
    expect(screen.queryByTestId("activity-signal")).not.toBeInTheDocument();
  });
});
