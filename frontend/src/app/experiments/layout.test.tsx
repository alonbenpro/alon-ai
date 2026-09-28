import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExperimentsLayout from "@/app/experiments/layout";
import { getSession } from "@/lib/operator/server";

vi.mock("next/image", () => ({
  default: function TestImage({ alt }: { alt: string }) { return <span role="img" aria-label={alt} />; },
}));
vi.mock("next/navigation", () => ({ redirect: vi.fn(), useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/operator/server", () => ({ getSession: vi.fn() }));

beforeEach(() => {
  vi.mocked(getSession).mockResolvedValue({
    kind: "authenticated",
    session: {
      authenticated: true,
      operator: { id: "operator-1", display_name: "Alon" },
    },
  } as Awaited<ReturnType<typeof getSession>>);
});

describe("experiments layout", () => {
  it("keeps the workspace navigation and controls visible", async () => {
    render(await ExperimentsLayout({ children: <div>Experiment intake</div> }));

    expect(screen.getByRole("link", { name: /system status/i })).toHaveAttribute("href", "/#system");
    expect(screen.getByRole("link", { name: /activity log/i })).toHaveAttribute("href", "/#activity");
    expect(screen.getByRole("button", { name: /Motion on/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign out/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /new experiment/i })).toHaveAttribute("aria-current", "page");
  });
});
