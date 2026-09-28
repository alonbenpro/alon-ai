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
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); sessionStorage.clear(); });

describe("experiment creation checkpoint", () => {
  it("starts from one optional idea field without asking for a mission brief", () => {
    render(<ExperimentCreation runtime={runtime} />);
    expect(screen.getByRole("heading", { name: "New experiment" })).toBeInTheDocument();
    expect(screen.getByText(/Recorded demo · example output/i)).toBeInTheDocument();
    expect(screen.queryByText(/One idea is enough/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Experiment preview")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Your idea" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate an idea" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start experiment" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Objective" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Target customer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Research budget (USD)" })).not.toBeInTheDocument();
  });

  it("does not discard typed idea text through the generate action", () => {
    render(<ExperimentCreation runtime={runtime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "My exact idea" } });
    expect(screen.getByRole("button", { name: "Generate an idea" })).toBeDisabled();
  });

  it("starts a supplied idea with only exact text and one command, then restores its run with GET", async () => {
    const started = { ...saved, idea_seed: "  Clinic idea\n", state: "REFINEMENT_IN_PROGRESS",
      draft: false, stage: "IDEA_REFINEMENT", stage_status: "RUNNING", latest_run_id: "run-1" };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(started)).mockResolvedValue(Response.json(started));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation runtime={runtime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "  Clinic idea\n" } });
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ idea_seed: "  Clinic idea\n", command_key: expect.any(String) });
    first.unmount();
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url, init]) => String(url).includes("/experiments") && init?.method === "POST")).toHaveLength(1);
  });

  it("generates proposals without creating a canonical experiment and preserves edited lineage", async () => {
    const draft = { ...saved, draft: true, mode: "SYSTEM_DISCOVERY", idea_seed: null, state: "AWAITING_SELECTION",
      stage: "IDEA_DISCOVERY", stage_status: "WAITING_FOR_INPUT", candidates,
      proposal_history: candidates.map((item, index) => ({ artifact_id: item.artifact_id, version: index + 1,
        parent_artifact_id: null, title: item.title, hypothesis: item.hypothesis, origin: "GENERATED", run_id: "run-generate" })) };
    const edited = { ...draft, candidates: [...candidates, { ...candidates[1], artifact_id: "revision-1", hypothesis: "  New wording\n" }],
      proposal_history: [...draft.proposal_history, { artifact_id: "revision-1", version: 4,
        parent_artifact_id: "candidate-2", title: "Queue visibility", hypothesis: "  New wording\n",
        idea_seed: "  New wording\n", origin: "OPERATOR_EDIT", run_id: null }] };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(draft)).mockResolvedValueOnce(Response.json(edited));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={runtime} />);
    fireEvent.click(screen.getByRole("button", { name: "Generate an idea" }));
    expect(await screen.findByText("Clinic intake")).toBeInTheDocument();
    expect(fetcher.mock.calls[0][0]).toBe("/api/operator/ideas/generate");
    fireEvent.click(screen.getByRole("radio", { name: /queue visibility/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Refine this proposal" }), { target: { value: "  New wording\n" } });
    expect(screen.getByRole("button", { name: "Start experiment" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Keep edited version" }));
    expect(await screen.findByText("v4 · Your edit")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start experiment" })).toBeEnabled();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/ideas/exp-1/revisions");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({ candidate_artifact_id: "candidate-2", idea_seed: "  New wording\n" });
  });

  it("starts the chosen revision through one server command and restores the same run", async () => {
    const draft = { ...saved, draft: true, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "AWAITING_SELECTION", stage: "IDEA_DISCOVERY", stage_status: "WAITING_FOR_INPUT", candidates };
    const started = { ...draft, draft: false, idea_seed: "Queue visibility", state: "REFINEMENT_IN_PROGRESS",
      stage: "IDEA_REFINEMENT", stage_status: "RUNNING", latest_run_id: "run-2" };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(draft)).mockResolvedValueOnce(Response.json(started))
      .mockResolvedValue(Response.json(started));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("radio", { name: /queue visibility/i }));
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/ideas/exp-1/start");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ candidate_artifact_id: "candidate-2", command_key: expect.any(String) });
    first.unmount();
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("keeps generation and revision history visible after reopening a draft", async () => {
    const history = [{ artifact_id: "candidate-2", version: 1, parent_artifact_id: null, title: "Queue visibility",
      hypothesis: "Reduce missed appointments", origin: "GENERATED", run_id: "run-generate" },
      { artifact_id: "revision-1", version: 2, parent_artifact_id: "candidate-2", title: "Queue visibility",
        hypothesis: "  Exact operator edit\n", idea_seed: "  Exact operator edit\n", origin: "OPERATOR_EDIT", run_id: null }];
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, draft: true, mode: "SYSTEM_DISCOVERY",
      idea_seed: null, state: "AWAITING_SELECTION", candidates, proposal_history: history,
      stage: "IDEA_DISCOVERY", stage_status: "WAITING_FOR_INPUT" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText("v2 · Your edit")).toBeInTheDocument();
    expect(screen.getByText(/Earlier versions/).closest("details")).not.toHaveAttribute("open");
    expect(screen.getByRole("heading", { name: "Pick a direction" })).toBeInTheDocument();
    expect(screen.queryByText(/Proposal session ID/)).not.toBeInTheDocument();
    expect(screen.getByText(/Exact operator edit/).textContent).toBe("  Exact operator edit\n");
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("keeps proposal provenance visible after starting the selected revision", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, draft: false,
      state: "AWAITING_REVIEW", latest_run_id: "run-2", advice,
      stage: "IDEA_REFINEMENT", stage_status: "WAITING_FOR_INPUT",
      proposal_history: [{ artifact_id: "revision-1", version: 2, parent_artifact_id: "candidate-2",
        title: "Queue visibility", hypothesis: "  Exact operator edit\n", idea_seed: "  Exact operator edit\n",
        origin: "OPERATOR_EDIT", run_id: null }] }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText("v2 · Your edit")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("shows a targeted profile block instead of inventing setup values", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ detail: "OPERATOR_PROFILE_REQUIRED" }, { status: 409 }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={runtime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "Clinic idea" } });
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/operator profile/i);
    expect(screen.getByRole("button", { name: "Start experiment" })).toBeEnabled();
    expect(screen.queryByRole("textbox", { name: "Objective" })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("keeps disabled live mode blocked and never switches to recorded mode", () => {
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={{ provider_mode: "disabled", ready: false }} />);
    expect(screen.getByText("Runtime blocked")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate an idea" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Start experiment" })).toBeDisabled();
    expect(screen.queryByText("Recorded demo mode")).not.toBeInTheDocument();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("requires explicit confirmation before a live idea launch", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, draft: false,
      stage: "IDEA_REFINEMENT", stage_status: "RUNNING", state: "REFINEMENT_IN_PROGRESS" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation runtime={{ provider_mode: "live", ready: true }} />);
    expect(screen.getByText(/generate directions with the Idea agent/i)).toBeInTheDocument();
    expect(screen.queryByText(/recorded example directions/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "Clinic idea" } });
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/confirm the live call/i);
    expect(fetcher).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("checkbox", { name: /may incur a cost/i }));
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("labels live generated directions without calling them recorded examples", async () => {
    const draft = { ...saved, draft: true, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "AWAITING_SELECTION", stage: "IDEA_DISCOVERY", stage_status: "WAITING_FOR_INPUT", candidates };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(draft)));
    render(<ExperimentCreation experimentId="exp-1" runtime={{ provider_mode: "live", ready: true }} />);
    expect(await screen.findByText("Generated directions")).toBeInTheDocument();
    expect(screen.queryByText("Recorded directions")).not.toBeInTheDocument();
  });

  it("regenerates from a chosen proposal and keeps previous versions", async () => {
    const draft = { ...saved, draft: true, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "AWAITING_SELECTION", stage: "IDEA_DISCOVERY", stage_status: "WAITING_FOR_INPUT", candidates,
      proposal_history: [{ artifact_id: "candidate-2", version: 1, parent_artifact_id: null,
        title: "Queue visibility", hypothesis: "Reduce missed appointments", origin: "GENERATED", run_id: "run-1" }] };
    const regenerated = { ...draft, proposal_history: [...draft.proposal_history,
      { artifact_id: "candidate-3", version: 2, parent_artifact_id: "candidate-2",
        title: "Follow-up reminders", hypothesis: "Reduce no-shows", origin: "GENERATED", run_id: "run-2" }] };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(draft)).mockResolvedValueOnce(Response.json(regenerated));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("radio", { name: /queue visibility/i }));
    fireEvent.click(screen.getByRole("button", { name: "Try more directions" }));
    expect(await screen.findByText("v2 · Generated")).toBeInTheDocument();
    expect(screen.getByText("v1 · Generated")).toBeInTheDocument();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/ideas/exp-1/generate");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toMatchObject({ candidate_artifact_id: "candidate-2" });
  });

  it("does not offer another generation while saved discovery is running", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ ...saved, draft: true,
      mode: "SYSTEM_DISCOVERY", idea_seed: null, state: "DISCOVERY_IN_PROGRESS",
      stage: "IDEA_DISCOVERY", stage_status: "RUNNING", candidates: [] }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText(/Idea discovery in progress/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try more directions" })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("retries a safely failed supplied first run without a research return", async () => {
    const failed = { ...saved, draft: false, state: "REFINEMENT_FAILED", retry_safe: true,
      stage: "IDEA_REFINEMENT", stage_status: "BLOCKED", blocked_reason: "REFINEMENT_FAILED", latest_run_id: "run-1" };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(failed))
      .mockResolvedValueOnce(Response.json({ run_id: "run-2", state: "AWAITING_REVIEW", advice, advice_source: "RECORDED_FAKE" }))
      .mockResolvedValueOnce(Response.json({ ...failed, state: "AWAITING_REVIEW", retry_safe: false,
        stage_status: "WAITING_FOR_INPUT", blocked_reason: null, latest_run_id: "run-2", advice,
        advice_source: "RECORDED_FAKE" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry refinement" }));
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/experiments/exp-1/refine");
    expect(JSON.parse(fetcher.mock.calls[1][1].body).idempotency_key).not.toBe("run-1");
    expect(await screen.findByText("Waiting for input")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("retries a safely failed draft discovery through the draft generation command", async () => {
    const failed = { ...saved, draft: true, mode: "SYSTEM_DISCOVERY", idea_seed: null,
      state: "DISCOVERY_FAILED", retry_safe: true, stage: "IDEA_DISCOVERY",
      stage_status: "BLOCKED", blocked_reason: "DISCOVERY_FAILED", candidates: [] };
    const ready = { ...failed, state: "AWAITING_SELECTION", retry_safe: false,
      stage_status: "WAITING_FOR_INPUT", blocked_reason: null, candidates };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(failed)).mockResolvedValueOnce(Response.json(ready));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry discovery" }));
    expect(await screen.findByText("Clinic intake")).toBeInTheDocument();
    expect(fetcher.mock.calls[1][0]).toBe("/api/operator/ideas/exp-1/generate");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ command_key: expect.any(String) });
  });

  it("continues a historical experiment that is awaiting its first refinement", async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json(saved));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByRole("button", { name: "Refine idea" })).toBeEnabled();
  });

  it("retries an ambiguous initial command with the same body after reload", async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error("connection lost"))
      .mockResolvedValueOnce(Response.json({ ...saved, draft: false, state: "REFINEMENT_IN_PROGRESS",
        stage: "IDEA_REFINEMENT", stage_status: "RUNNING" }));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<ExperimentCreation runtime={runtime} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Your idea" }), { target: { value: "  Clinic idea\n" } });
    fireEvent.click(screen.getByRole("button", { name: "Start experiment" }));
    expect(await screen.findByRole("button", { name: "Retry start" })).toBeInTheDocument();
    first.unmount();
    render(<ExperimentCreation runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry start" }));
    expect(await screen.findByText("Agent running")).toBeInTheDocument();
    expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
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
    expect(screen.getByText(/Suggested relationship: Clarifies core intent/)).toBeInTheDocument();
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

  it("marks recorded advice as an example rather than a live agent result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...saved, state: "AWAITING_REVIEW",
      latest_run_id: "run-1", advice, advice_source: "RECORDED_FAKE" })));
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByText("Recorded example · no live agent ran")).toBeInTheDocument();
    expect(screen.getByText("Full suggested idea and open questions").closest("details")).not.toHaveAttribute("open");
  });

  it("shows the exact proposed title even when its selected direction had a shorter name", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...saved, mode: "SYSTEM_DISCOVERY",
      state: "AWAITING_REVIEW", candidates, selected_candidate_artifact_id: "candidate-1",
      latest_run_id: "run-1", advice, advice_source: "RECORDED_FAKE" })));
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);
    expect(await screen.findByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(screen.getByText(/Selected direction:/)).toHaveTextContent("Clinic intake");
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
    expect(within(screen.getByRole("region", { name: /review the proposed change/i })).getByText(/cannot be accepted here/i)).toBeInTheDocument();
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

  it("shows committed feedback and the prior accepted brief before starting a bounded return", async () => {
    const returnAvailable = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: {
        artifact_id: "idea-1", version: 1, content_hash: "prior-hash",
        payload: { ...advice, buyer: { segment: "Independent clinics", role: "Operations lead" },
          service_hypothesis: "A scheduling workflow setup", value_hypothesis: "Fewer manual requests",
          assumptions: ["Clinic staff own intake"], exclusions: ["No clinical advice"],
          research_questions: ["Will clinics pay for setup?"] },
      },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash",
        payload: { preserve: ["Clinic scheduling"], change: ["Narrow to intake"],
          evidence_summary: "Two operators reported intake delays" },
        failed_dimensions: ["Willingness to pay"] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" },
      return_lineage: [{ return_id: "return-1", ordinal: 1, from_cycle_id: "cycle-1",
        to_cycle_id: "cycle-2", verdict_id: "verdict-1", prior_brief_artifact_id: "idea-1",
        feedback_artifact_id: "feedback-1" }],
    };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ ...saved, state: "RETURN_REVIEW_REQUIRED",
      accepted_brief: returnAvailable.prior_brief.payload, return_available: returnAvailable }));
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    expect(await screen.findByRole("heading", { name: "Research feedback return" })).toBeInTheDocument();
    expect(screen.getByText("Two operators reported intake delays")).toBeInTheDocument();
    expect(screen.getByText("Clinic scheduling")).toBeInTheDocument();
    expect(screen.getByText("Willingness to pay")).toBeInTheDocument();
    expect(screen.getByText(/research cycle: research-cycle-1/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start refinement from committed feedback" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
  });

  it("retries the exact committed-feedback command before allowing returned refinement", async () => {
    const returnAvailable = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: { artifact_id: "idea-1", version: 1, content_hash: "prior-hash", payload: advice },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash",
        payload: { preserve: ["Clinic scheduling"] }, failed_dimensions: ["Willingness to pay"] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" },
      return_lineage: [],
    };
    const returnState = { ...saved, state: "RETURN_REVIEW_REQUIRED", return_available: returnAvailable };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(returnState))
      .mockRejectedValueOnce(new Error("lost return response"))
      .mockResolvedValueOnce(Response.json(returnState))
      .mockResolvedValueOnce(Response.json({ experiment_id: "exp-1", cycle_id: "cycle-2", state: "AWAITING_REFINEMENT" }));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    fireEvent.click(await screen.findByRole("button", { name: "Start refinement from committed feedback" }));
    expect(await screen.findByRole("button", { name: "Retry return refinement" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry return refinement" }));

    expect(await screen.findByRole("button", { name: "Refine returned idea" })).toBeEnabled();
    expect(fetcher.mock.calls[3][1].body).toBe(fetcher.mock.calls[1][1].body);
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({
      verdict_id: "verdict-1", command_key: expect.any(String), feedback: {
        artifact_id: "feedback-1", kind: "RESEARCH_FEEDBACK_BRIEF", version: 1,
        content_hash: "feedback-hash", role: "RESEARCH_FEEDBACK",
      },
    });
  });

  it("keeps a server validation failure visible after refreshing return status", async () => {
    const returnAvailable = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: { artifact_id: "idea-1", version: 1, content_hash: "prior-hash", payload: advice },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash", payload: { preserve: ["Clinic scheduling"] }, failed_dimensions: [] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" }, return_lineage: [],
    };
    const returnState = { ...saved, state: "RETURN_REVIEW_REQUIRED", return_available: returnAvailable };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(returnState))
      .mockResolvedValueOnce(Response.json({ detail: [{ loc: ["body", "feedback", "role"] }] }, { status: 422 }))
      .mockResolvedValueOnce(Response.json(returnState));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    fireEvent.click(await screen.findByRole("button", { name: "Start refinement from committed feedback" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Review role: the server rejected this value.");
    expect(screen.getByRole("button", { name: "Retry return refinement" })).toBeInTheDocument();
  });

  it("replaces a return failure with the fail-closed status message when refresh fails", async () => {
    const returnAvailable = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: { artifact_id: "idea-1", version: 1, content_hash: "prior-hash", payload: advice },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash", payload: { preserve: ["Clinic scheduling"] }, failed_dimensions: [] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" }, return_lineage: [],
    };
    const returnState = { ...saved, state: "RETURN_REVIEW_REQUIRED", return_available: returnAvailable };
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(returnState))
      .mockResolvedValueOnce(Response.json({ detail: "FORGED_RESEARCH_FEEDBACK" }, { status: 409 }))
      .mockRejectedValueOnce(new Error("status offline"));
    vi.stubGlobal("fetch", fetcher);
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    fireEvent.click(await screen.findByRole("button", { name: "Start refinement from committed feedback" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Saved status is unavailable. No new run will start until the server confirms its state.");
    expect(screen.getByRole("button", { name: "Retry return refinement" })).toBeDisabled();
  });

  it("clears a pending return command when refresh confirms its child cycle", async () => {
    const returnContext = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: { artifact_id: "idea-1", version: 1, content_hash: "prior-hash", payload: advice },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash", payload: { preserve: ["Clinic scheduling"] }, failed_dimensions: [] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" }, return_lineage: [],
    };
    sessionStorage.setItem("experiment-exp-1-return-pending", JSON.stringify({ verdict_id: "verdict-1",
      feedback: { artifact_id: "feedback-1", kind: "RESEARCH_FEEDBACK_BRIEF", version: 1,
        content_hash: "feedback-hash", role: "RESEARCH_FEEDBACK" }, command_key: "return-key" }));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...saved, state: "AWAITING_REFINEMENT",
      cycle_purpose: "SAME_INTENT_RETURN", return_context: returnContext })));

    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    await screen.findByRole("button", { name: "Refine returned idea" });
    expect(sessionStorage.getItem("experiment-exp-1-return-pending")).toBeNull();
  });

  it("shows a durable repeated-blocker review state without another return action", async () => {
    const returnAvailable = {
      verdict_id: "verdict-3", research_cycle_id: "research-cycle-3",
      prior_brief: { artifact_id: "idea-3", version: 3, content_hash: "prior-hash", payload: advice },
      feedback: { artifact_id: "feedback-3", version: 1, content_hash: "feedback-hash", payload: { preserve: ["Clinic scheduling"] }, failed_dimensions: ["Willingness to pay"] },
      evidence: { report_artifact_id: "report-3", recommendation_artifact_id: "recommendation-3" }, return_lineage: [],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...saved, state: "RETURN_REVIEW_REQUIRED",
      return_available: returnAvailable, return_review: { reason_code: "REPEATED_BLOCKER",
        verdict_id: "verdict-3", research_cycle_id: "research-cycle-3" } })));
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    expect(await screen.findByRole("heading", { name: "Operator review required" })).toBeInTheDocument();
    expect(screen.getByText(/same blocker returned again/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start refinement from committed feedback" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refine returned idea" })).not.toBeInTheDocument();
  });

  it("compares the returned proposal with the committed prior version before acceptance", async () => {
    const prior = { ...advice, buyer: { segment: "Independent clinics", role: "Operations lead" },
      service_hypothesis: "Scheduling workflow setup", value_hypothesis: "Fewer manual requests",
      assumptions: ["Staff own intake"], exclusions: ["No clinical advice"], research_questions: ["Will clinics pay?"] };
    const returnedAdvice = { ...prior, title: "Intake workflow for clinics", service_hypothesis: "Intake-only workflow setup",
      value_hypothesis: "Faster intake triage", research_questions: ["Will clinics pay for intake setup?"] };
    const returnAvailable = {
      verdict_id: "verdict-1", research_cycle_id: "research-cycle-1",
      prior_brief: { artifact_id: "idea-1", version: 1, content_hash: "prior-hash", payload: prior },
      feedback: { artifact_id: "feedback-1", version: 1, content_hash: "feedback-hash", payload: { change: ["Narrow to intake"] }, failed_dimensions: [] },
      evidence: { report_artifact_id: "report-1", recommendation_artifact_id: "recommendation-1" }, return_lineage: [],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ ...saved, state: "AWAITING_REVIEW",
      latest_run_id: "run-return-1", advice: returnedAdvice, accepted_brief: prior, return_context: returnAvailable })));
    render(<ExperimentCreation experimentId="exp-1" runtime={runtime} />);

    fireEvent.click(await screen.findByText("Full suggested idea and open questions"));
    expect(screen.getByText("Intake-only workflow setup")).toBeInTheDocument();
    expect(screen.getAllByText("Independent clinics · Operations lead")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeInTheDocument();
  });
});
