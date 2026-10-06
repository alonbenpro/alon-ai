import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExperimentCreation } from "@/components/experiments/experiment-creation";
import { RunInspector } from "@/components/agent-lab/run-inspector";
import type { components } from "@/lib/api/schema";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));

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
    payload: { origin: "USER_SUPPLIED", statement: idea } }],
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

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); sessionStorage.clear(); });

describe("R01A live idea run inspector", () => {
  it("shows actual model messages and failed output separately from the saved result", async () => {
    const exchangeEvents = { events: [
      { sequence: 3, at: "2026-10-05T10:00:03Z", type: "MODEL_RESPONSE", detail: "Visible model output",
        exchange: { model_request_number: 1, tool_name: null, tool_call_id: null, status: "FAILED",
          payload: { parts: [{ part_kind: "text", content: "I could not verify clinic demand." }], finish_reason: "stop", state: "FAILED" },
          omissions: ["Hidden reasoning and provider signatures are not included."] } },
      { sequence: 2, at: "2026-10-05T10:00:02Z", type: "MODEL_REQUEST", detail: "Actual model request",
        exchange: { model_request_number: 1, tool_name: null, tool_call_id: null, status: "PREPARED",
          payload: { model_identifier: "gpt-live", messages: [{ kind: "request", instructions: "Evaluate the clinic market.",
            parts: [{ part_kind: "user-prompt", content: "Explore independent clinics in Israel." }] }],
            parameters: { function_tools: [{ name: "brave_search" }], output_object: { type: "object" } }, settings: { max_tokens: 4000 } },
          omissions: [] } }
    ] };
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method && init.method !== "GET") throw new Error("Opening a trace must not submit a command");
      const path = String(input);
      if (path.endsWith("/events")) return Response.json(exchangeEvents);
      if (path.endsWith("/result")) return Response.json({ ...result, status: "FAILED", output: null });
      return Response.json({ ...run, status: "FAILED", output: null });
    });
    vi.stubGlobal("fetch", fetcher);
    const view = render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    const exchanges = await screen.findByRole("region", { name: "Requests and responses" });
    const trace = within(exchanges);
    expect(trace.getByText("I could not verify clinic demand.")).toBeVisible();
    expect(trace.getByText("Hidden reasoning and provider signatures are not included.")).toBeVisible();
    const request = trace.getByText("View model request #1").closest("details")!;
    expect(request).not.toHaveAttribute("open");
    fireEvent.click(within(request).getByText("View model request #1"));
    expect(trace.getByText("Evaluate the clinic market.")).toBeVisible();
    expect(trace.getByText("Explore independent clinics in Israel.")).toBeVisible();
    fireEvent.click(within(request).getByText("Complete model request #1 JSON"));
    expect(within(request).getByText(/"max_tokens": 4000/)).toBeVisible();
    const cards = exchanges.querySelectorAll("article");
    expect(cards[0]).toHaveTextContent("Model request #1");
    expect(cards[1]).toHaveTextContent("Model response #1");
    expect(screen.getByRole("heading", { name: "Request context" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Saved result" })).toBeInTheDocument();
    view.unmount();
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    expect(await screen.findByRole("region", { name: "Requests and responses" })).toHaveTextContent("I could not verify clinic demand.");
    expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  });

  it("exposes tool arguments, retained source text, and unavailable historical content honestly", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json({ events: [
        { sequence: 1, at: "2026-10-05T10:00:01Z", type: "TOOL_REQUEST", exchange: {
          model_request_number: 1, tool_name: "read_evidence", tool_call_id: "tool-clinic-1", status: "PREPARED",
          payload: { arguments: { retained_id: "evidence-clinic-1", max_chars: 2500 } }, omissions: [] } },
        { sequence: 2, at: "2026-10-05T10:00:02Z", type: "TOOL_RESPONSE", exchange: {
          model_request_number: 1, tool_name: "read_evidence", tool_call_id: "tool-clinic-1", status: "COMPLETED",
          payload: { result: { type: "retained_evidence_excerpt", reference: { retained_id: "evidence-clinic-1" },
            text: "Clinic owners report missed appointments every week.", availability: "AVAILABLE" } }, omissions: [] } },
        { sequence: 3, at: "2026-10-05T10:00:03Z", type: "TOOL_RESPONSE", exchange: {
          model_request_number: 1, tool_name: "brave_search", tool_call_id: "tool-search-2", status: "UNAVAILABLE",
          payload: { result: { observed_count: 4, availability: "TRANSIENT_RESULT_NOT_RETAINED" } },
          omissions: ["Transient Brave search results were not retained."] } },
        { sequence: 4, at: "2026-10-05T10:00:04Z", type: "MODEL_RESPONSE", detail: "Old response", exchange: null }
      ] });
      if (path.endsWith("/result")) return Response.json(result);
      return Response.json(run);
    }));
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    const trace = within(await screen.findByRole("region", { name: "Requests and responses" }));
    fireEvent.click(trace.getByText("View tool request · read_evidence · tool-clinic-1"));
    expect(trace.getByText("2500")).toBeVisible();
    fireEvent.click(trace.getByText("View tool response · read_evidence · tool-clinic-1"));
    expect(trace.getByText("Clinic owners report missed appointments every week.")).toBeVisible();
    expect(trace.getByText("Transient Brave search results were not retained.")).toBeVisible();
    expect(trace.getByText(/Actual exchange content is unavailable for this event/)).toBeVisible();
    expect(trace.getByText("No payload was retained.")).toBeVisible();
  });

  it("replaces live exchange payloads when polling without starting a paid rerun", async () => {
    vi.useFakeTimers();
    let completed = false;
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method && init.method !== "GET") throw new Error("Polling must only read");
      const path = String(input);
      if (path.endsWith("/events")) return Response.json({ events: [{ sequence: 1, at: "2026-10-05T10:00:01Z",
        type: "MODEL_RESPONSE", exchange: { model_request_number: 1, tool_name: null, tool_call_id: null,
          status: completed ? "COMPLETED" : "PREPARED", payload: { parts: [{ part_kind: "text",
            content: completed ? "Polling returned the completed model output." : "The model is still running." }] }, omissions: [] } }] });
      if (path.endsWith("/result")) return Response.json(result);
      return Response.json({ ...run, status: completed ? "SUCCEEDED" : "RUNNING", finished_at: completed ? run.finished_at : null });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(screen.getByText("The model is still running.")).toBeVisible();
    completed = true;
    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(screen.getByText("Polling returned the completed model output.")).toBeVisible();
    expect(screen.queryByText("The model is still running.")).not.toBeInTheDocument();
    expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  });

  it("keeps tool failure messages and structured model output readable", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json({ events: [
        { sequence: 1, at: "2026-10-05T10:00:01Z", type: "TOOL_RESPONSE", exchange: {
          model_request_number: 1, tool_name: "capture_url", tool_call_id: "tool-capture-1", status: "FAILED",
          payload: { error: { stage: "capture", error_type: "ResearchToolError", code: "RESEARCH_UNAVAILABLE",
            message: "The clinic source could not be captured.", frames: [] } }, omissions: [] } },
        { sequence: 2, at: "2026-10-05T10:00:02Z", type: "MODEL_RESPONSE", exchange: {
          model_request_number: 2, tool_name: null, tool_call_id: null, status: "COMPLETED",
          payload: { parts: [{ part_kind: "text", content: '{"finding":"Demand remains uncertain.","open_questions":["Who pays?"]}' }] } } }
      ] });
      if (path.endsWith("/result")) return Response.json(result);
      return Response.json(run);
    }));
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    const trace = within(await screen.findByRole("region", { name: "Requests and responses" }));
    expect(trace.getByText("The clinic source could not be captured.")).toBeVisible();
    expect(trace.getByText("Demand remains uncertain.")).toBeVisible();
    expect(trace.getByText("Who pays?")).toBeVisible();
    const complete = trace.getByText("Complete model response #2 JSON").closest("details")!;
    expect(complete).not.toHaveAttribute("open");
    fireEvent.click(within(complete).getByText("Complete model response #2 JSON"));
    expect(complete).toHaveTextContent('\\"finding\\":\\"Demand remains uncertain.\\"');
  });

  it("explains when an older run has no captured exchanges", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json(result);
      return Response.json(run);
    }));
    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);
    const trace = await screen.findByRole("region", { name: "Requests and responses" });
    expect(trace).toHaveTextContent("Actual model and tool exchange content was not retained for this run.");
    expect(trace).toHaveTextContent("Request context and saved result are shown separately below.");
  });

  it("shows the retained IDEA_SEED statement without rendering an empty research count", async () => {
    const retainedStatement = "AI agents and workflows for small clinics";
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json({ events: [] });
      if (path.endsWith("/result")) return Response.json({ ...result, output: null, status: "BLOCKED" });
      return Response.json({ ...run, status: "BLOCKED", phase: "BLOCKED", output: null,
        research_gaps: [], resolved_inputs: [{ ...run.resolved_inputs![0],
          payload: { origin: "USER_SUPPLIED", statement: retainedStatement } }] });
    }));

    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);

    expect(await screen.findByText(retainedStatement)).toBeInTheDocument();
    expect(screen.queryByText("No saved idea input was returned.")).not.toBeInTheDocument();
    expect(screen.queryByText(/^0$/)).not.toBeInTheDocument();
  });

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
    expect(screen.getByText("Cost details").closest("details")).not.toHaveAttribute("open");
  });

  it("waits for reconciliation when a provider receipt is unresolved and does not repeat its diagnostic code", async () => {
    const unresolvedReceipt = { receipt_id: "receipt-brave", provider: "BRAVE", model_identifier: null,
      state: "OUTCOME_UNKNOWN", currency: "USD", reserved: "0.01", accrued: "0.01", usage: [] };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json({ events: [{ sequence: 1, at: "2026-10-02T10:00:00Z",
        type: "RESEARCH_RESPONSE", detail: "RESEARCH_TOOL_UNAVAILABLE", diagnostic: {
          stage: "research", error_type: "ResearchToolError", code: "RESEARCH_TOOL_UNAVAILABLE",
          message: "A research tool was unavailable for this request.", frames: [] } }] });
      if (path.endsWith("/result")) return Response.json({ ...result, status: "OUTCOME_UNKNOWN", actual_cost_usd: null,
        receipts: [unresolvedReceipt] });
      return Response.json({ ...run, status: "OUTCOME_UNKNOWN", phase: "OUTCOME_UNKNOWN", actual_cost_usd: null,
        pending_cost_usd: null, receipts: [unresolvedReceipt] });
    }));

    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);

    expect((await screen.findAllByText("Awaiting reconciliation")).length).toBeGreaterThan(0);
    expect(screen.getByText("RESEARCH_TOOL_UNAVAILABLE")).toBeInTheDocument();
    expect(screen.queryByText("RESEARCH_TOOL_UNAVAILABLE · RESEARCH_TOOL_UNAVAILABLE")).not.toBeInTheDocument();
  });

  it("shows provider request activity while keeping receipts in technical details", async () => {
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
    const providerDetails = (await screen.findByText("Provider call details")).closest("details")!;
    expect(providerDetails).not.toHaveAttribute("open");
    fireEvent.click(within(providerDetails).getByText("Provider call details"));
    expect(providerDetails).toHaveAttribute("open");
    expect(screen.getByText("receipt-1")).toBeInTheDocument();
    expect(screen.getByText("incomplete")).toBeInTheDocument();
    expect(screen.getByText("Initial buyer evidence is limited")).toBeInTheDocument();
    expect(screen.getByText(/Buyer budget unknown/)).toBeInTheDocument();
    expect(screen.getByText(/Provider receipts \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/Result finding-1 · Call call-1/)).toBeInTheDocument();
  });

  it("shows a retained diagnostic with the failed stage and safe error details", async () => {
    const diagnosticRun = {
      ...run, status: "BLOCKED" as const, phase: "BLOCKED" as const, output: null,
      blocked_reason: "REFINEMENT_UNAVAILABLE",
      diagnostic: {
        stage: "research request", error_type: "ResearchToolError", code: "RESEARCH_TOOL_UNAVAILABLE",
        message: "Brave search could not complete within the approved request limit.",
        frames: ["ResearchToolError: request limit exceeded"],
      },
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/events")) return Response.json(events);
      if (path.endsWith("/result")) return Response.json({ ...result, status: "BLOCKED", output: null,
        diagnostic: diagnosticRun.diagnostic });
      return Response.json(diagnosticRun);
    }));

    render(<RunInspector experimentId="exp-r01a" runId="run-r01a" />);

    expect(await screen.findByRole("heading", { name: "Run error" })).toBeInTheDocument();
    expect(screen.getByText("research request")).toBeInTheDocument();
    expect(screen.getByText("ResearchToolError")).toBeInTheDocument();
    expect(screen.getByText(/Brave search could not complete/)).toBeInTheDocument();
    expect(screen.getByText("Diagnostic frames").closest("details")).not.toHaveAttribute("open");
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

    expect((await screen.findAllByText("$0.0123")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Agent activity" })).toBeInTheDocument();
    const inspectorElement = screen.getByRole("region", { name: /agent activity/i });
    const inspector = within(inspectorElement);
    expect(inspectorElement.querySelector(".agent-run-inspector__idea")).toHaveTextContent(idea.replace("\n", " "));
    expect(screen.getByRole("heading", { name: advice.title })).toBeInTheDocument();
    expect(inspector.getAllByText(/Staff lose time following up on missed appointments/).length).toBeGreaterThan(0);
    expect(inspector.getByText("Live · complete")).toBeInTheDocument();
    expect(inspector.getByText("7s")).toBeInTheDocument();
    expect(inspector.getByText("$0.0000")).toBeInTheDocument();
    expect(inspector.getAllByText("$0.0123").length).toBeGreaterThan(0);
    expect(inspector.getByText(/250/)).toBeInTheDocument();
    expect(inspector.getByText("Request context")).toBeInTheDocument();
    expect(inspector.getByText("Saved result")).toBeInTheDocument();
    expect(inspector.getByText("View saved result").closest("details")).not.toHaveAttribute("open");
    expect(inspector.getByText("Cost details").closest("details")).not.toHaveAttribute("open");
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
    const inspector = within(screen.getByRole("region", { name: /agent activity/i }));
    expect(inspector.getAllByText(/Staff lose time following up on missed appointments/).length).toBeGreaterThan(0);
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
    const inspector = within(screen.getByRole("region", { name: /agent activity/i }));
    expect(inspector.getAllByText(/Staff lose time following up on missed appointments/).length).toBeGreaterThan(0);
  });
});
