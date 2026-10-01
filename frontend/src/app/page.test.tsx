import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Home from "@/app/page";
import { backendFetch, getSession } from "@/lib/operator/server";

vi.mock("next/image", () => ({
  default: function TestImage({ alt }: { alt: string }) { return <span role="img" aria-label={alt} />; },
}));
vi.mock("next/navigation", () => ({ redirect: vi.fn(), usePathname: () => "/" }));
vi.mock("@/lib/operator/server", () => ({
  backendFetch: vi.fn(),
  getSession: vi.fn(),
}));
vi.mock("@/components/operator/activity-feed", () => ({
  ActivityFeed: () => <div>Activity feed</div>,
}));
vi.mock("@/components/operator/status-overview", () => ({
  StatusOverview: () => <div>Status overview</div>,
}));
vi.mock("@/components/operator/operator-controls", () => ({
  OperatorControls: () => <div>Operator controls</div>,
}));

beforeEach(() => {
  vi.mocked(getSession).mockResolvedValue({
    kind: "authenticated",
    session: {
      authenticated: true,
      operator: { id: "operator-1", display_name: "Alon" },
    },
  } as Awaited<ReturnType<typeof getSession>>);
  vi.mocked(backendFetch).mockResolvedValue({ ok: false } as Response);
});

describe("operator home", () => {
  it("offers an authenticated path to create an experiment", async () => {
    render(await Home());

    expect(screen.getByRole("link", { name: /new experiment/i })).toHaveAttribute("href", "/experiments/new");
  });
});
