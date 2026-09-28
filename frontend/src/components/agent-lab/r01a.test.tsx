import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExperimentCreation } from "@/components/experiments/experiment-creation";
import { RunInspector } from "@/components/agent-lab/run-inspector";
import type { components } from "@/lib/api/schema";

const runtime = { provider_mode: "live", ready: true } as const;
const idea = "Help clinics reduce missed appointments.\nStart with independent practices in Israel.";
const advice = {
  title: "Appointment recovery for clinics",
  customer: "Independent clinics",
  problem: "Staff lose time following up on missed appointments",
  core_intent: "Help clinics recover missed appointments",
  material_pivot: false,
  intent_relationship: "CLARIFIES_CORE_INTENT",
  grounding_refs: ["SEED", "OPERATOR_PROFILE"],
  uncertainties: ["Will clinic owners pay for this?"]
};
const experiment = {
  experiment_id: "exp-r01a",
  name: "Appointment recovery",
  mode: "USER_SEEDED_REFINEMENT",
  idea_seed: idea,
  brief: {},
  state: "AWAITING_REVIEW",
  candidates: [],
  selected_candidate_artifact_id: null,
  latest_run_id: "run-r01a",
  advice,
  advice_source: "OPENAI",
  accepted_brief: null,
  retry_safe: false,
  draft: false,
  stage: "IDEA_REFINEMENT",
  stage_status: "WAITING_FOR_INPUT"
};
const run = {
  run_id: "run-r01a",
  experiment_id: "exp-r01a",
  task_kind: "IDEA_REFINEMENT",
  status: "SUCCEEDED",
  research_status: "ASSESSED",
  phase: "WAITING_FOR_OPERATOR",
  provider_mode: "live",
  created_at: "2026-09-28T08:00:00Z",
  started_at: "2026-09-28T08:00:01Z",
  finished_at: "2026-09-28T08:00:08Z",
  outcome: "IDEA_PROPOSED",
  blocked_reason: null,
  resolved_inputs: [{ artifact_id: "seed-r01a", kind: "IDEA_SEED", version: 1, content_hash: "abc", role: "SEED",
    payload: { idea_seed: idea } }],
  output: advice,
  advice_source: "OPENAI",
  model_identifier: "gpt-live",
  profile_id: "profile-1",
  profile_version: 2,
  operator_profile: { profile_id: "profile-1", version: 2, content_hash: "profile-hash",
    capabilities: ["Interview independent clinic owners"], constraints: ["No unapproved outreach"] },
  receipt_id: "receipt-1",
  pending_cost_usd: "0.0000",
  actual_cost_usd: "0.0123",
  usage: [{ component: "openai", quantity: "250", cost: "0.0123", currency: "USD", knowledge: "FINAL" }],
  review_status: "PENDING",
  cancel_requested: false,
  cancel_confirmed: false
} satisfies components["schemas"]["RunView"];
const result = {
  run_id: "run-r01a",
  status: "SUCCEEDED",
  research_status: "ASSESSED",
  output: advice,
  advice_source: "OPENAI",
  receipt_id: "receipt-1",
  actual_cost_usd: "0.0123",
  usage: [{ component: "openai", quantity: "250", cost: "0.0123", currency: "USD", knowledge: "FINAL" }]
} satisfies components["schemas"]["RunResult"];
const events = { events: [
  { sequence: 1, at: "2026-09-28T08:00:01Z", type: "RUN_STARTED", detail: "Idea refinement started" },
  { sequence: 2, at: "2026-09-28T08:00:08Z", type: "RUN_SUCCEEDED", detail: "Idea proposal is ready for review" }
] } satisfies components["schemas"]["RunEvents"];

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); sessionStorage.clear(); });

describe("R01A live idea run inspector", () => {
  it("labels recorded ledger cost without implying a paid provider charge", async () => {
    const recorded = { ...run, provider_mode: "fake" as const, advice_source: "RECORDED_FAKE" };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json({ ...result, advice_source: "RECORDED_FAKE" });
      return Response.json(recorded);
    }));
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    expect(await screen.findByText("Recorded ledger cost")).toBeInTheDocument();
    expect(screen.queryByText("Actual cost")).not.toBeInTheDocument();
  });

  it("shows retained child steps and the parent receipt when the run includes them", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json(result);
      return Response.json({ ...run, research_status: "INCOMPLETE", research_gaps: ["Buyer budget unknown"],
        research_summary: { finding: "Initial buyer evidence is limited", limitations: ["One segment"],
          unresolved_questions: ["Who signs the contract?"] },
        receipts: [{ receipt_id: "receipt-brave", provider: "BRAVE", model_identifier: null,
          state: "FINAL", currency: "USD", reserved: "0.01", accrued: "0.01", usage: [] }],
        steps: [{ step_key: "step-1", ordinal: 1,
        kind: "BRAVE_SEARCH", status: "SUCCEEDED", result_artifact_id: "finding-1", provider_call_id: "call-1" }] });
    }));
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    expect(await screen.findByText("Child steps and receipts")).toBeInTheDocument();
    expect(screen.getByText("receipt-1")).toBeInTheDocument();
    expect(screen.getByText("INCOMPLETE")).toBeInTheDocument();
    expect(screen.getByText("Initial buyer evidence is limited")).toBeInTheDocument();
    expect(screen.getByText(/Buyer budget unknown/)).toBeInTheDocument();
    expect(screen.getByText(/Provider receipts \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Result finding-1 · Call call-1/)).toBeInTheDocument();
  });

  it("reopens the saved run with exact input, output, cost, and separate review without starting another run", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      void init;
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json(experiment);
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json(run);
      if (path === "/api/operator/agent-runs/run-r01a/events") return Response.json(events);
      if (path === "/api/operator/agent-runs/run-r01a/result") return Response.json(result);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);

    expect(await screen.findByText("$0.0123")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent run" })).toBeInTheDocument();
    const inspector = within(screen.getByRole("region", { name: /agent run/i }));
    expect(inspector.getByText((_text, node) => node?.tagName === "PRE" && node.textContent === idea)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(inspector.getByText(/Staff lose time following up on missed appointments/)).toBeInTheDocument();
    expect(inspector.getByText("Live · complete")).toBeInTheDocument();
    expect(inspector.getByText("7s")).toBeInTheDocument();
    expect(inspector.getByText("$0.0000")).toBeInTheDocument();
    expect(inspector.getByText("$0.0123")).toBeInTheDocument();
    expect(inspector.getByText(/250/)).toBeInTheDocument();
    expect(inspector.getByText("Interview independent clinic owners")).toBeInTheDocument();
    expect(inspector.getByText(/SEED · OPERATOR_PROFILE/)).toBeInTheDocument();
    expect(inspector.getByText("RUN SUCCEEDED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Reject run" })).toBeInTheDocument();
    expect(fetcher.mock.calls.every(([, init]) => init?.method !== "POST")).toBe(true);
  });

  it("shows a blocked credential error and does not present output for review", async () => {
    const blockedRun = { ...run, status: "BLOCKED", outcome: null, blocked_reason: "LIVE_CONFIG_REQUIRED",
      output: null, phase: "BLOCKED", review_status: "PENDING", finished_at: "2026-09-28T08:00:08Z" };
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json({ ...experiment,
        state: "REFINEMENT_BLOCKED", latest_run_id: "run-r01a", advice: null, stage_status: "BLOCKED" });
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json(blockedRun);
      if (path.endsWith("/events")) return Response.json({ events: [] });
      if (path.endsWith("/result")) return Response.json({ run_id: "run-r01a", status: "BLOCKED", output: null,
        advice_source: null, receipt_id: null, actual_cost_usd: null });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);

    expect(await screen.findByText(/LIVE_CONFIG_REQUIRED/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
  });

  it("keeps unrelated live output visible but prevents acceptance", async () => {
    const unrelated = { ...advice, intent_relationship: "UNRELATED" };
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json({ ...experiment,
        advice: unrelated, state: "AWAITING_REVIEW" });
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json({ ...run, output: unrelated });
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json({ ...result, output: unrelated });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);

    expect(await screen.findByText(/unrelated proposal cannot be accepted here/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject run" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept and save idea" })).toBeDisabled();
  });

  it("keeps an unconfirmed cancellation visible after the run becomes outcome unknown", async () => {
    let cancellationRequested = false;
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json({ ...experiment,
        state: "REFINEMENT_IN_PROGRESS", advice: null, stage_status: "RUNNING" });
      if (path.endsWith("/cancel") && init?.method === "POST") {
        cancellationRequested = true;
        return Response.json({ run_id: "run-r01a", requested: true, confirmed: false, status: "OUTCOME_UNKNOWN" });
      }
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json({ ...run, status: cancellationRequested ? "OUTCOME_UNKNOWN" : "RUNNING",
        outcome: null, finished_at: null, cancel_requested: cancellationRequested, cancel_confirmed: false });
      if (path.endsWith("/events")) return Response.json({ events: [] });
      if (path.endsWith("/result")) return Response.json({ run_id: "run-r01a", status: "OUTCOME_UNKNOWN",
        output: null, advice_source: null, receipt_id: null, actual_cost_usd: null, usage: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);
    fireEvent.click(await screen.findByRole("button", { name: "Cancel run" }));

    expect(await screen.findByText(/service has not confirmed that the run stopped/i)).toBeInTheDocument();
    const cancelCall = fetcher.mock.calls.find(([url, init]) => String(url).endsWith("/cancel") && init?.method === "POST");
    expect(cancelCall).toBeDefined();
    expect(JSON.parse(String(cancelCall?.[1]?.body))).toEqual({ command_key: expect.any(String) });
  });

  it("records rejection separately and removes the accept action for that saved run", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json(experiment);
      if (path.endsWith("/reject") && init?.method === "POST") return Response.json({ ...run, phase: "REJECTED", review_status: "REJECTED" });
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json(run);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json(result);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);
    fireEvent.change(await screen.findByRole("textbox", { name: "Reason for rejecting run" }), {
      target: { value: "The proposal changed the core intent." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject run" }));

    expect(await screen.findByText(/This run was rejected/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
    const rejectCall = fetcher.mock.calls.find(([url, init]) => String(url).endsWith("/reject") && init?.method === "POST");
    expect(JSON.parse(String(rejectCall?.[1]?.body))).toMatchObject({
      command_key: expect.any(String), reason: "The proposal changed the core intent.",
    });
  });

  it("restores a persisted rejection after reload and keeps its exact output available", async () => {
    const rejectedRun = { ...run, phase: "REJECTED", review_status: "REJECTED" } satisfies components["schemas"]["RunView"];
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json(experiment);
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json(rejectedRun);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json(result);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);

    expect(await screen.findByText(/This run was rejected/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept and save idea" })).not.toBeInTheDocument();
    const inspector = within(screen.getByRole("region", { name: /agent run/i }));
    expect(inspector.getByText(/Staff lose time following up on missed appointments/)).toBeInTheDocument();
  });

  it("keeps exact output visible and explains a capability denial from acceptance", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/operator/experiments/exp-r01a") return Response.json(experiment);
      if (path.endsWith("/accept") && init?.method === "POST") {
        return Response.json({ detail: "CAPABILITY_UNSUPPORTED" }, { status: 409 });
      }
      if (path === "/api/operator/agent-runs/run-r01a") return Response.json(run);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json(result);
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ExperimentCreation experimentId="exp-r01a" runtime={runtime} />);
    fireEvent.change(await screen.findByRole("combobox", { name: /intent relationship/i }), {
      target: { value: "CLARIFIES_CORE_INTENT" },
    });
    fireEvent.click(screen.getByRole("checkbox", { name: /confirm this classification/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Reason for classification" }), {
      target: { value: "It keeps the clinic scheduling intent." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Accept and save idea" }));

    expect(await screen.findByText(/output needs a capability this Idea agent does not have/i)).toBeInTheDocument();
    const inspector = within(screen.getByRole("region", { name: /agent run/i }));
    expect(inspector.getByText(/Staff lose time following up on missed appointments/)).toBeInTheDocument();
  });
});
