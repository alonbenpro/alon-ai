import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiStatus } from "@/components/api-status";
import { fetchReadiness } from "@/lib/api/readiness";

vi.mock("@/lib/api/readiness", () => ({
  fetchReadiness: vi.fn(),
}));

const mockedFetchReadiness = vi.mocked(fetchReadiness);

function renderStatus() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ApiStatus />
    </QueryClientProvider>,
  );
}

describe("ApiStatus", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("does not claim services are online while readiness is pending", () => {
    mockedFetchReadiness.mockReturnValue(new Promise(() => undefined));

    renderStatus();

    expect(screen.getByText("Checking services…")).toBeInTheDocument();
    expect(screen.queryByText("API online")).not.toBeInTheDocument();
    expect(screen.queryByText("Database online")).not.toBeInTheDocument();
    expect(
      screen.getByText("Outreach disabled by default"),
    ).toBeInTheDocument();
    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
    expect(liveRegion).toHaveAttribute("aria-atomic", "true");
    expect(liveRegion).toContainElement(screen.getByText("Checking services…"));
    expect(liveRegion).not.toContainElement(
      screen.getByText("Outreach disabled by default"),
    );
  });

  it("reports both services online after a ready response", async () => {
    mockedFetchReadiness.mockResolvedValue({
      database: "up",
      status: "ready",
    });

    renderStatus();

    expect(await screen.findByText("API online")).toBeInTheDocument();
    expect(screen.getByText("Database online")).toBeInTheDocument();
    expect(
      screen.getByText("Outreach disabled by default"),
    ).toBeInTheDocument();
  });

  it("reports services unavailable without false online claims", async () => {
    mockedFetchReadiness.mockRejectedValue(new Error("network unavailable"));

    renderStatus();

    expect(await screen.findByText("Services unavailable")).toBeInTheDocument();
    expect(screen.queryByText("API online")).not.toBeInTheDocument();
    expect(screen.queryByText("Database online")).not.toBeInTheDocument();
    expect(
      screen.getByText("Outreach disabled by default"),
    ).toBeInTheDocument();
  });
});
