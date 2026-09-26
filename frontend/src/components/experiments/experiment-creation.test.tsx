import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExperimentCreation } from "@/components/experiments/experiment-creation";

const runtime = { provider_mode: "fake", ready: true } as const;
const advice = {
  title: "Appointment workflow for clinics", customer: "Independent clinics",
  problem: "Staff reconcile requests manually", core_intent: "A scheduling workflow for clinics",
  material_pivot: false, intent_relationship: "CLARIFIES_CORE_INTENT",
  grounding_refs: ["SEED", "OPERATOR_PROFILE"],
  uncertainties: ["Will clinics pay?"],
};
const brief = {
  objective: "Test demand", target_customer: "Clinics", problem: "Manual scheduling",
  geographies: ["Israel"], commercial_boundaries: "No guarantees", budget_usd: "25",
  evidence_definitions: ["Buyer interviews"], launch_stage: "SHADOW",
};
const saved = {
  experiment_id: "exp-1", name: "Clinic scheduling", mode: "USER_SEEDED_REFINEMENT",
  idea_seed: "  Original seed  ", brief, state: "AWAITING_REFINEMENT",
  candidates: [], selected_candidate_artifact_id: null, latest_run_id: null,
  advice: null, advice_source: null, accepted_brief: null, retry_safe: false,
};
const candidates = [
  { artifact_id: "candidate-1", title: "Clinic intake", hypothesis: "Reduce intake time", demand_status: "UNVERIFIED", uncertainties: ["Buyer budget"] },
  { artifact_id: "candidate-2", title: "Queue visibility", hypothesis: "Reduce missed appointments", demand_status: "UNVERIFIED", uncertainties: ["Workflow fit"] },
  { artifact_id: "candidate-3", title: "Follow-up reminders", hypothesis: "Reduce no-shows", demand_status: "UNVERIFIED", uncertainties: ["Consent"] },
];
function fillRequiredFields() {
  const values: Record<string, string> = {
    "Experiment name": "Clinic scheduling", "Your idea": "  Original seed  ", "Objective": "Test demand",
    "Target customer": "Clinics", "Problem hypothesis": "Manual scheduling", "Geographies": "Israel",
    "Commercial boundaries": "No guarantees", "Research budget (USD)": "25",
    "Evidence definitions": "Buyer interviews", "Capabilities": "Web applications",
    "Constraints": "No regulated data", "Maximum project hours": "120", "Hours per week": "20",
    "Concurrent projects": "1", "Hourly cost": "75", "Minimum project price": "3000",
    "Minimum margin rate": "0.30", "Maximum discount rate": "0.10", "Minimum deposit rate": "0.25",
  };
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value } });
  }
  fireEvent.change(screen.getByRole("combobox", { name: "Currency" }), { target: { value: "USD" } });
}
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); sessionStorage.clear(); });

describe("experiment creation checkpoint", () => {
  it("preserves the exact seed and requires complete bounds", async () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={runtime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "  Clinic idea\n" } });
    expect(screen.getByTestId("seed-preview").textContent).toBe("  Clinic idea\n");
    fireEvent.click(screen.getByRole("button", { name: "Create experiment" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/complete the experiment bounds/i);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("reuses an ambiguous create command without changing its payload", async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error("connection lost"))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", state: "AWAITING_REFINEMENT" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={runtime} />); fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create experiment" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry creation" }));
    expect(await screen.findByText(/Experiment ID: exp-1/)).toBeInTheDocument();
    expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
    expect(JSON.parse(fetcher.mock.calls[0][1].body).idea_seed).toBe("  Original seed  ");
  });

  it("creates system discovery without a seed, shows three candidates and requires an explicit selection", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", state: "AWAITING_DISCOVERY" }))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", state: "AWAITING_SELECTION", candidates }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={runtime} />); fillRequiredFields();
    fireEvent.click(screen.getByRole("radio", { name: /system discovery/i }));
    fireEvent.click(screen.getByRole("button", { name: "Create experiment" }));
    expect(await screen.findByRole("button", { name: "Discover directions" })).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).not.toHaveProperty("idea_seed");
    fireEvent.click(screen.getByRole("button", { name: "Discover directions" }));
    expect(await screen.findByText("Clinic intake")).toBeInTheDocument();
    expect(screen.getByText("Queue visibility")).toBeInTheDocument();
    expect(screen.getByText("Follow-up reminders")).toBeInTheDocument();
    expect(screen.getAllByText(/demand is unverified/i)).toHaveLength(2);
    expect(screen.getAllByText(/unverified demand/i)).toHaveLength(3);
    expect(screen.queryByRole("button", { name: "Refine selected direction" })).not.toBeInTheDocument();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/experiments/exp-1/discover");
  });

  it("waits for the selection receipt before enabling refinement", async () => {
    let finish!: (value: Response) => void;
    const selection = new Promise<Response>((resolve) => { finish = resolve; });
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ ...saved, mode: "SYSTEM_DISCOVERY",
      idea_seed: null, state: "AWAITING_SELECTION", candidates }))
      .mockReturnValueOnce(selection);
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("radio", { name: /queue visibility/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /reason for selection/i }), { target: { value: "Fits current delivery capacity" } });
    fireEvent.click(screen.getByRole("button", { name: "Select direction" }));
    expect(screen.queryByRole("button", { name: "Refine selected direction" })).not.toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[1][1].body).candidate_artifact_id).toBe("candidate-2");
    finish(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1", selection_id: "selection-1", state: "AWAITING_REFINEMENT" }));
    expect(await screen.findByRole("button", { name: "Refine selected direction" })).toBeEnabled();
  });

  it("retries the exact pending selection command after reload", async () => {
    const selectionState = { ...saved, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "AWAITING_SELECTION", candidates };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(selectionState))
      .mockRejectedValueOnce(new Error("lost selection response"))
      .mockResolvedValueOnce(Response.json(selectionState))
      .mockResolvedValueOnce(Response.json(selectionState))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1",
        selection_id: "selection-1", state: "AWAITING_REFINEMENT" }));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("radio", { name: /queue visibility/i }));
    fireEvent.change(screen.getByRole("textbox", { name: /reason for selection/i }),
      { target: { value: "Fits current delivery capacity" } });
    fireEvent.click(screen.getByRole("button", { name: "Select direction" }));
    expect(await screen.findByRole("button", { name: "Retry selection" })).toBeInTheDocument();
    first.unmount();

    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry selection" }));
    expect(await screen.findByRole("button", { name: "Refine selected direction" })).toBeEnabled();
    expect(fetcher.mock.calls[4][1].body).toBe(fetcher.mock.calls[1][1].body);
    expect(sessionStorage.length).toBe(0);
  });

  it("recovers selected discovery and advice from GET after refresh", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "AWAITING_REVIEW", candidates, selected_candidate_artifact_id: "candidate-2",
      latest_run_id: "run-1", advice, advice_source: "RECORDED_FAKE" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(screen.getByText(/selected direction/i)).toBeInTheDocument();
    expect(screen.getByText("Queue visibility")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("offers a fresh refinement key only after GET confirms a safe terminal retry", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(saved))
      .mockRejectedValueOnce(new Error("lost response"))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "REFINEMENT_IN_PROGRESS", retry_safe: false }))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "REFINEMENT_FAILED", retry_safe: true }))
      .mockResolvedValueOnce(Response.json({ run_id: "run-2", state: "AWAITING_REVIEW", advice }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Refine idea" }));
    expect(await screen.findByText(/refinement in progress/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry refinement" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry refinement" }));
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    const first = JSON.parse(fetcher.mock.calls[1][1].body).idempotency_key;
    const second = JSON.parse(fetcher.mock.calls[4][1].body).idempotency_key;
    expect(second).not.toBe(first);
  });

  it("does not offer a new run while saved status is unavailable", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(saved))
      .mockRejectedValueOnce(new Error("lost response"))
      .mockRejectedValueOnce(new Error("status offline"));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Refine idea" }));
    expect(await screen.findByRole("button", { name: "Check status" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refine idea" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry refinement" })).not.toBeInTheDocument();
  });

  it("reuses the same refinement key after refresh while the attempt is ambiguous", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(saved))
      .mockRejectedValueOnce(new Error("lost response"))
      .mockResolvedValueOnce(Response.json(saved))
      .mockResolvedValueOnce(Response.json(saved))
      .mockResolvedValueOnce(Response.json({ state: "AWAITING_REVIEW", run_id: "run-1", advice }));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Refine idea" }));
    await screen.findByRole("button", { name: "Refine idea" });
    first.unmount();
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Refine idea" }));
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[4][1].body).idempotency_key)
      .toBe(JSON.parse(fetcher.mock.calls[1][1].body).idempotency_key);
  });

  it("keeps polling a saved in-progress run until the server confirms completion", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ ...saved, state: "REFINEMENT_IN_PROGRESS" }))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "REFINEMENT_IN_PROGRESS" }))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "AWAITING_REVIEW", latest_run_id: "run-1", advice }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(screen.getByText(/refinement in progress/i)).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(fetcher).toHaveBeenCalledTimes(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("requires relationship classification and explicit confirmation to accept advice", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ ...saved, state: "AWAITING_REVIEW",
      latest_run_id: "run-1", advice }))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", idea_brief_artifact_id: "idea-1", state: "IDEA_ACCEPTED" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    const accept = await screen.findByRole("button", { name: "Accept and save idea" });
    expect(screen.getByText("Model suggestion: Clarifies core intent")).toBeInTheDocument();
    expect(accept).toBeDisabled();
    fireEvent.change(screen.getByRole("combobox", { name: /intent relationship/i }), { target: { value: "NARROWS_CORE_INTENT" } });
    expect(accept).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /confirm this classification/i }));
    expect(accept).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox", { name: /reason for classification/i }), { target: { value: "Same clinics, narrower workflow" } });
    fireEvent.click(accept);
    expect(await screen.findByText(/experiment ready/i)).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({
      run_id: "run-1", intent_relationship: "NARROWS_CORE_INTENT", intent_confirmed: true,
      intent_rationale: "Same clinics, narrower workflow",
    });
  });

  it("retries the exact pending acceptance command after reload", async () => {
    const reviewState = { ...saved, state: "AWAITING_REVIEW", latest_run_id: "run-1", advice };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(reviewState))
      .mockRejectedValueOnce(new Error("lost acceptance response"))
      .mockResolvedValueOnce(Response.json(reviewState))
      .mockResolvedValueOnce(Response.json(reviewState))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", idea_brief_artifact_id: "idea-1",
        state: "IDEA_ACCEPTED" }));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    const accept = await screen.findByRole("button", { name: "Accept and save idea" });
    fireEvent.change(screen.getByRole("combobox", { name: /intent relationship/i }),
      { target: { value: "NARROWS_CORE_INTENT" } });
    fireEvent.change(screen.getByRole("textbox", { name: /reason for classification/i }),
      { target: { value: "Same clinics, narrower workflow" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /confirm this classification/i }));
    fireEvent.click(accept);
    expect(await screen.findByRole("button", { name: "Retry acceptance" })).toBeInTheDocument();
    first.unmount();

    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry acceptance" }));
    expect(await screen.findByText(/experiment ready/i)).toBeInTheDocument();
    expect(fetcher.mock.calls[4][1].body).toBe(fetcher.mock.calls[1][1].body);
    expect(sessionStorage.length).toBe(0);
  });

  it.each(["MATERIAL_PIVOT", "UNRELATED"])("blocks %s acceptance in the normal path", async (category) => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, state: "AWAITING_REVIEW",
      latest_run_id: "run-1", advice })); vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    const select = await screen.findByRole("combobox", { name: /intent relationship/i });
    fireEvent.change(select, { target: { value: category } });
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeDisabled();
    expect(within(screen.getByRole("region", { name: /idea review/i })).getByText(/cannot be accepted here/i)).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("blocks acceptance when the model proposes an unrelated relationship", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, state: "AWAITING_REVIEW",
      latest_run_id: "run-1", advice: { ...advice, intent_relationship: "UNRELATED" } }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    const select = await screen.findByRole("combobox", { name: /intent relationship/i });
    fireEvent.change(select, { target: { value: "PRESERVES_CORE_INTENT" } });
    fireEvent.change(screen.getByRole("textbox", { name: /reason for classification/i }), { target: { value: "This appears to preserve the direction" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /confirm this classification/i }));
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeDisabled();
    expect(screen.getByText(/unrelated proposal cannot be accepted here/i)).toBeInTheDocument();
  });
});
