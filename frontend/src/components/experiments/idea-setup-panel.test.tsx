import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IdeaSetupPanel } from "./idea-setup-panel";

const profile = {
  capabilities: ["Python development", "AI automation"], constraints: ["Personal projects"],
  delivery: { max_project_hours: "80", hours_per_week: "20", concurrent_projects: 1 },
  commercial: { currency: "ILS", hourly_cost: "150", minimum_project_price: "2000",
    minimum_margin_rate: "0.3", maximum_discount_rate: "0.1", minimum_deposit_rate: "0.5" },
};
const saved = { profile_id: "profile-1", profile_version: 1, profile, budget_usd: "0.25" };
afterEach(() => vi.unstubAllGlobals());

describe("operator profile setup", () => {
  it("loads saved values and submits an intentional edit through the profile endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(saved))
      .mockResolvedValueOnce(Response.json({ profile_id: "profile-1", profile_version: 2, budget_usd: "0.25" }));
    vi.stubGlobal("fetch", fetcher);
    render(<IdeaSetupPanel />);
    expect(await screen.findByRole("textbox", { name: "Capabilities" })).toHaveValue("Python development\nAI automation");
    fireEvent.change(screen.getByRole("textbox", { name: "Capabilities" }), { target: { value: "Python development\nWorkflow automation" } });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Profile saved · version 2");
    expect(fetcher).toHaveBeenLastCalledWith("/api/operator/idea-profile", expect.objectContaining({ method: "POST",
      body: JSON.stringify({ profile: { ...profile, capabilities: ["Python development", "Workflow automation"] } }) }));
    expect(screen.getByRole("link", { name: "Start an experiment" })).toHaveAttribute("href", "/experiments/new");
  });

  it("does not invent an operator's missing terms", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ profile: null, profile_id: null, profile_version: null, budget_usd: "0.25" })));
    render(<IdeaSetupPanel />);
    expect(await screen.findByText("No profile saved yet.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Capabilities" })).toHaveValue("");
    expect(screen.getByLabelText("Currency")).toHaveValue("");
    expect(screen.getByLabelText("Hours per week")).toHaveValue(null);
  });

  it("keeps the editor blocked when saved state cannot be read", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
    render(<IdeaSetupPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load your profile");
    expect(screen.queryByRole("button", { name: "Save profile" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry loading" })).toBeInTheDocument();
  });
});
