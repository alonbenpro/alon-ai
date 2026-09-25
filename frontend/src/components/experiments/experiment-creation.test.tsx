import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExperimentCreation } from "@/components/experiments/experiment-creation";

const advice = {
  title: "Appointment workflow for neighborhood clinics",
  customer: "Independent clinics",
  problem: "Staff manually reconcile appointment requests",
  core_intent: "Build a simple scheduling workflow for clinics",
  material_pivot: false,
  grounding_refs: ["SEED", "OPERATOR_PROFILE"],
  uncertainties: ["Whether clinics will pay for integration work"],
};
const demoRuntime = { provider_mode: "fake", ready: true } as const;

function fillRequiredFields() {
  const values: Record<string, string> = {
    "Experiment name": "Clinic scheduling",
    "Your idea": "  I want to build scheduling tools for clinics.  ",
    "Objective": "Test demand for appointment automation",
    "Target customer": "Independent clinics",
    "Problem hypothesis": "Appointment requests are handled manually",
    "Geographies": "Israel",
    "Commercial boundaries": "No guarantees or paid integrations",
    "Research budget (USD)": "25",
    "Evidence definitions": "Three independent buyer interviews",
    "Capabilities": "Web applications",
    "Constraints": "No regulated patient data",
    "Maximum project hours": "120",
    "Hours per week": "20",
    "Concurrent projects": "1",
    "Hourly cost": "75",
    "Minimum project price": "3000",
    "Minimum margin rate": "0.30",
    "Maximum discount rate": "0.10",
    "Minimum deposit rate": "0.25",
  };
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value } });
  }
  fireEvent.change(screen.getByRole("combobox", { name: "Currency" }), { target: { value: "USD" } });
}

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("user-seeded experiment creation", () => {
  it("previews the seed exactly as entered and keeps the first launch stage in shadow", () => {
    render(<ExperimentCreation runtime={demoRuntime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), {
      target: { value: "  Clinic scheduling\nwith a queue  " },
    });

    expect(screen.getByTestId("seed-preview").textContent).toBe("  Clinic scheduling\nwith a queue  ");
    expect(screen.getByText("SHADOW")).toBeInTheDocument();
    expect(screen.getByText(/recorded demo mode/i)).toBeInTheDocument();
  });

  it("requires explicit acknowledgment before a live paid refinement call", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1", brief_artifact_id: "brief-1", seed_artifact_id: "seed-1", state: "AWAITING_REFINEMENT" }))
      .mockResolvedValueOnce(Response.json({ run_id: "run-1", outcome: "ADVICE_READY", advice, advice_source: "OPENAI", state: "AWAITING_REVIEW" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={{ provider_mode: "live", ready: true }} />);
    fillRequiredFields();

    expect(screen.getByText(/live OpenAI refinement/i)).toBeInTheDocument();
    expect(within(screen.getByRole("note")).getByText(/research budget/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/confirm the live call/i);
    expect(fetcher).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("checkbox", { name: /I understand this may incur a cost/i }));
    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("blocks creation when the runtime is unavailable", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={{ provider_mode: "disabled", ready: false }} />);
    fillRequiredFields();

    expect(screen.getByText(/refinement is unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create and refine" })).toBeDisabled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("keeps entered data and blocks creation when required bounds are missing", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={demoRuntime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), {
      target: { value: "Scheduling for clinics" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/complete the experiment bounds/i);
    expect(screen.getByRole("textbox", { name: "Your idea" })).toHaveValue("Scheduling for clinics");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("creates, refines and waits for explicit acceptance before showing success", async () => {
    let resolveAcceptance: ((response: Response) => void) | undefined;
    const acceptPending = new Promise<Response>((resolve) => { resolveAcceptance = resolve; });
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1", brief_artifact_id: "brief-1", seed_artifact_id: "seed-1", state: "AWAITING_REFINEMENT" }))
      .mockResolvedValueOnce(Response.json({ run_id: "run-1", outcome: "ADVICE_READY", advice, advice_source: "RECORDED_FAKE", state: "AWAITING_REVIEW" }))
      .mockReturnValueOnce(acceptPending);
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={demoRuntime} />);
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(screen.getByText("Recorded demo advice")).toBeInTheDocument();
    expect(screen.getByText("Whether clinics will pay for integration work")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Starting assumptions" })).getByText("Appointment requests are handled manually")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Unknowns to test" })).getByText("Whether clinics will pay for integration work")).toBeInTheDocument();
    expect(screen.getByTestId("seed-preview").textContent).toBe("  I want to build scheduling tools for clinics.  ");
    expect(screen.queryByText(/experiment ready/i)).not.toBeInTheDocument();

    const createBody = JSON.parse(fetcher.mock.calls[0][1].body as string);
    expect(createBody.idea_seed).toBe("  I want to build scheduling tools for clinics.  ");
    expect(createBody.brief.geographies).toEqual(["Israel"]);
    expect(createBody.brief.launch_stage).toBe("SHADOW");
    expect(createBody.operator_profile.commercial.currency).toBe("USD");
    expect(createBody.command_key).toMatch(/^[0-9a-f-]{36}$/i);
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/experiments/exp-1/refine");

    fireEvent.click(screen.getByRole("button", { name: "Accept and save idea" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    expect(screen.queryByText(/experiment ready/i)).not.toBeInTheDocument();
    const acceptBody = JSON.parse(fetcher.mock.calls[2][1].body as string);
    expect(acceptBody.run_id).toBe("run-1");
    expect(acceptBody.command_key).toMatch(/^[0-9a-f-]{36}$/i);
    expect(acceptBody).not.toHaveProperty("advice");

    resolveAcceptance?.(Response.json({ experiment_id: "exp-1", idea_brief_artifact_id: "idea-1", acceptance_id: "accept-1", state: "IDEA_ACCEPTED" }));
    expect(await screen.findByText(/experiment ready/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view experiment/i })).toHaveAttribute("href", "/experiments/exp-1");
  });

  it("keeps a created experiment available for retry when refinement fails", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1", brief_artifact_id: "brief-1", seed_artifact_id: "seed-1", state: "AWAITING_REFINEMENT" }))
      .mockResolvedValueOnce(Response.json({ detail: "Refinement unavailable" }, { status: 503 }))
      .mockResolvedValueOnce(Response.json({ run_id: "run-2", outcome: "ADVICE_READY", advice, state: "AWAITING_REVIEW" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={demoRuntime} />);
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/refinement could not finish/i);
    fireEvent.click(screen.getByRole("button", { name: "Retry refinement" }));

    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls[2][0]).toBe("/api/operator/experiments/exp-1/refine");
  });

  it("recovers saved advice after refresh without creating or refining again", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({
      experiment_id: "exp-1", name: "Clinic scheduling", state: "AWAITING_REVIEW",
      brief: { objective: "Test demand", target_customer: "Clinics", problem: "Manual scheduling",
        geographies: ["Israel"], commercial_boundaries: "No guarantees", budget_usd: "25",
        evidence_definitions: ["Buyer interviews"], launch_stage: "SHADOW" },
      idea_seed: "  Original seed  ", cycle_id: "cycle-1", latest_run_id: "run-1",
      latest_outcome: "ADVICE_READY", advice, advice_source: "RECORDED_FAKE", accepted_brief: null,
    }));
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-1" runtime={demoRuntime} />);

    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(screen.getByText("Recorded demo advice")).toBeInTheDocument();
    expect(screen.getByTestId("seed-preview").textContent).toBe("  Original seed  ");
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeEnabled();
    expect(fetcher).toHaveBeenCalledOnce();
    expect(fetcher.mock.calls[0][0]).toBe("/api/operator/experiments/exp-1");
  });

  it("blocks acceptance of a material pivot", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-1", brief_artifact_id: "brief-1", seed_artifact_id: "seed-1", state: "AWAITING_REFINEMENT" }))
      .mockResolvedValueOnce(Response.json({ run_id: "run-1", outcome: "ADVICE_READY", advice: { ...advice, material_pivot: true }, advice_source: "OPENAI", state: "AWAITING_REVIEW" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={demoRuntime} />);
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/changes the original direction/i);
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("identifies a rejected field and retains inputs after server validation", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({
      detail: [{ loc: ["body", "brief", "target_customer"], msg: "Unsupported target" }],
    }, { status: 422 }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={demoRuntime} />);
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: "Create and refine" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/target customer/i);
    expect(screen.getByRole("textbox", { name: "Target customer" })).toHaveValue("Independent clinics");
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("shows the server-accepted brief after refresh even when advice is no longer returned", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({
      experiment_id: "exp-1", name: "Clinic scheduling", state: "IDEA_ACCEPTED",
      brief: { objective: "Test demand", target_customer: "Clinics", problem: "Manual scheduling",
        geographies: ["Israel"], commercial_boundaries: "No guarantees", budget_usd: "25",
        evidence_definitions: ["Buyer interviews"], launch_stage: "SHADOW" },
      idea_seed: "Original seed", cycle_id: "cycle-1", latest_run_id: "run-1",
      latest_outcome: "ADVICE_READY", advice: null, advice_source: "RECORDED_FAKE",
      accepted_brief: { title: advice.title, customer: advice.customer, problem: advice.problem,
        core_intent: advice.core_intent, material_pivot: false },
    }));
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-1" runtime={demoRuntime} />);

    expect(await screen.findByText(/experiment ready/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
  });

  it("waits for an in-progress saved refinement and does not dispatch another run", async () => {
    const saved = {
      experiment_id: "exp-1", name: "Clinic scheduling", idea_seed: "Original seed",
      brief: { objective: "Test demand", target_customer: "Clinics", problem: "Manual scheduling",
        geographies: ["Israel"], commercial_boundaries: "No guarantees", budget_usd: "25",
        evidence_definitions: ["Buyer interviews"], launch_stage: "SHADOW" },
      cycle_id: "cycle-1", latest_run_id: "run-1", latest_outcome: null,
      advice_source: "OPENAI", advice: null, accepted_brief: null,
    };
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ ...saved, state: "REFINEMENT_IN_PROGRESS" }))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "AWAITING_REVIEW", advice }));
    vi.stubGlobal("fetch", fetcher);
    vi.useFakeTimers();

    render(<ExperimentCreation experimentId="exp-1" runtime={demoRuntime} />);
    await vi.waitFor(() => expect(screen.getByText(/refinement in progress/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Retry refinement" })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(3000);
    await vi.waitFor(() => expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument());
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls.every((call) => call[0] === "/api/operator/experiments/exp-1")).toBe(true);
  });

  it("does not offer a new refinement when polling a running one loses connection", async () => {
    const saved = {
      experiment_id: "exp-1", name: "Clinic scheduling", idea_seed: "Original seed",
      brief: { objective: "Test demand", target_customer: "Clinics", problem: "Manual scheduling",
        geographies: ["Israel"], commercial_boundaries: "No guarantees", budget_usd: "25",
        evidence_definitions: ["Buyer interviews"], launch_stage: "SHADOW" },
      cycle_id: "cycle-1", latest_run_id: "run-1", latest_outcome: null,
      advice_source: "OPENAI", advice: null, accepted_brief: null,
      state: "REFINEMENT_IN_PROGRESS",
    };
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json(saved))
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(Response.json({ ...saved, state: "AWAITING_REVIEW", advice }));
    vi.stubGlobal("fetch", fetcher);
    vi.useFakeTimers();

    render(<ExperimentCreation experimentId="exp-1" runtime={{ provider_mode: "live", ready: true }} />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText(/refinement in progress/i)).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(screen.getByText(/status temporarily unavailable/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry refinement" })).not.toBeInTheDocument();

    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
