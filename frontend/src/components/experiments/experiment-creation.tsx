"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import type { components } from "@/lib/api/schema";

type Mode = "USER_SEEDED_REFINEMENT" | "SYSTEM_DISCOVERY";
type Relationship = "PRESERVES_CORE_INTENT" | "CLARIFIES_CORE_INTENT" | "NARROWS_CORE_INTENT" | "MATERIAL_PIVOT" | "UNRELATED";
type Brief = {
  title: string; customer: string; problem: string; core_intent: string;
  material_pivot: boolean;
  buyer?: { segment: string; role: string };
  service_hypothesis?: string; value_hypothesis?: string;
  assumptions?: string[]; exclusions?: string[]; research_questions?: string[];
};
type Advice = Brief & {
  intent_relationship: Relationship;
  grounding_refs: string[]; uncertainties: string[];
};
const relationshipLabels: Record<Relationship, string> = {
  PRESERVES_CORE_INTENT: "Preserves core intent",
  CLARIFIES_CORE_INTENT: "Clarifies core intent",
  NARROWS_CORE_INTENT: "Narrows core intent",
  MATERIAL_PIVOT: "Material pivot",
  UNRELATED: "Unrelated",
};
type Candidate = components["schemas"]["ProposalSnapshot"];
type ProposalRevision = components["schemas"]["ProposalRevisionSnapshot"];
type SelectionCommand = { candidate_artifact_id: string; reason: string; command_key: string };
type AcceptanceCommand = { run_id: string; command_key: string; intent_relationship: Relationship;
  intent_rationale: string; intent_confirmed: true };
type ReturnAvailable = {
  verdict_id: string; research_cycle_id: string;
  prior_brief: { artifact_id: string; version: number; content_hash: string; payload: Brief };
  feedback: { artifact_id: string; version: number; content_hash: string;
    payload: Record<string, unknown>; failed_dimensions: string[] };
  evidence: { report_artifact_id: string; recommendation_artifact_id: string };
  return_lineage: { return_id: string; ordinal: number; from_cycle_id: string; to_cycle_id: string;
    verdict_id: string; prior_brief_artifact_id: string; feedback_artifact_id: string }[];
};
type ReturnCommand = { verdict_id: string; feedback: { artifact_id: string; kind: "RESEARCH_FEEDBACK_BRIEF";
  version: number; content_hash: string; role: "RESEARCH_FEEDBACK" }; command_key: string };
type ReturnReview = { reason_code: "REPEATED_BLOCKER" | "SAME_INTENT_LIMIT_REACHED" | string;
  verdict_id: string; research_cycle_id: string };
type ServerState = "AWAITING_DISCOVERY" | "DISCOVERY_IN_PROGRESS" | "DISCOVERY_FAILED" | "DISCOVERY_BLOCKED" |
  "AWAITING_SELECTION" | "AWAITING_REFINEMENT" | "REFINEMENT_IN_PROGRESS" | "REFINEMENT_FAILED" |
  "REFINEMENT_BLOCKED" | "AWAITING_REVIEW" | "RETURN_REVIEW_REQUIRED" | "IDEA_ACCEPTED";
type Snapshot = components["schemas"]["ExperimentSnapshot"] & {
  state: ServerState;
  cycle_purpose?: string | null;
  advice: Advice | null; advice_source: "RECORDED_FAKE" | "OPENAI" | null; accepted_brief: Brief | null;
  return_available?: ReturnAvailable | null;
  return_context?: ReturnAvailable | null;
  return_review?: ReturnReview | null;
};
export type RuntimeReadiness = components["schemas"]["ExperimentRuntimeStatus"];

const draftKey = "experiment-create-pending";
const runKey = (experiment: string, action: "discover" | "refine") => `experiment-${experiment}-${action}-key`;
const commandKey = (experiment: string, action: "select" | "accept" | "return") => `experiment-${experiment}-${action}-pending`;
const draftCommandKey = (experiment: string) => `experiment-${experiment}-draft-command`;
function pendingCommand<T>(experiment: string, action: "select" | "accept" | "return"): T | null {
  try { return JSON.parse(sessionStorage.getItem(commandKey(experiment, action)) ?? "null") as T | null; }
  catch { return null; }
}
const running = (state: ServerState | null) => state === "DISCOVERY_IN_PROGRESS" || state === "REFINEMENT_IN_PROGRESS";
const failed = (state: ServerState | null) => state === "DISCOVERY_FAILED" || state === "REFINEMENT_FAILED";

async function post(path: string, payload: object) {
  const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload), cache: "no-store" });
  if (response.status === 401) { window.location.replace("/login"); throw new Error("SESSION_EXPIRED"); }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if (response.status === 422 && Array.isArray(error.detail)) {
      const field = error.detail[0]?.loc?.at(-1);
      if (typeof field === "string") throw new Error(`FIELD:${field.replaceAll("_", " ")}`);
    }
    throw new Error(typeof error.detail === "string" ? error.detail : "REQUEST_FAILED");
  }
  return response.json();
}
function failure(error: unknown, action: string) {
  const code = error instanceof Error ? error.message : "";
  if (code.startsWith("FIELD:")) return `Review ${code.slice(6)}: the server rejected this value.`;
  if (code === "SESSION_EXPIRED") return "Your session expired. Sign in again to continue.";
  if (code.includes("OPERATOR_PROFILE_REQUIRED")) return "Save your operator profile before starting an experiment.";
  if (code.includes("INTAKE_BUDGET_REQUIRED")) return "Set the research budget in workspace policy before starting an experiment.";
  if (code.includes("LIVE_CONFIG_REQUIRED")) return "Live mode is blocked until its provider is configured and authorized.";
  if (code.includes("UNRELATED")) return "An unrelated direction cannot be accepted here.";
  if (code.includes("MATERIAL_PIVOT")) return "A material pivot needs a separate approval decision.";
  return `${action} could not finish. Check the saved status before starting a new attempt.`;
}
const createBody = (ideaSeed: string, commandKey: string): components["schemas"]["CreateExperimentRequest"] =>
  ({ idea_seed: ideaSeed, command_key: commandKey });

function BriefDetails({ brief }: { brief: Brief }) {
  return <dl className="experiment-brief-details">
    <div><dt>Title</dt><dd>{brief.title}</dd></div>
    <div><dt>Customer</dt><dd>{brief.customer}</dd></div>
    <div><dt>Problem</dt><dd>{brief.problem}</dd></div>
    <div><dt>Core intent</dt><dd>{brief.core_intent}</dd></div>
    {brief.buyer && <div><dt>Buyer</dt><dd>{brief.buyer.segment} · {brief.buyer.role}</dd></div>}
    {brief.service_hypothesis && <div><dt>Service hypothesis</dt><dd>{brief.service_hypothesis}</dd></div>}
    {brief.value_hypothesis && <div><dt>Value hypothesis</dt><dd>{brief.value_hypothesis}</dd></div>}
    {brief.assumptions && <div><dt>Assumptions</dt><dd>{brief.assumptions.join(" · ")}</dd></div>}
    {brief.exclusions && <div><dt>Exclusions</dt><dd>{brief.exclusions.join(" · ")}</dd></div>}
    {brief.research_questions && <div><dt>Research questions</dt><dd>{brief.research_questions.join(" · ")}</dd></div>}
  </dl>;
}

function feedbackValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => feedbackValue(item)).join(" · ");
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value);
}

function returnReviewMessage(reason: ReturnReview["reason_code"]) {
  if (reason === "REPEATED_BLOCKER") return "The same blocker returned again. Review the direction before continuing.";
  if (reason === "SAME_INTENT_LIMIT_REACHED") return "Two same-intent returns have already been used. Review the direction before continuing.";
  return "This research return needs operator review before another refinement can start.";
}

export function ExperimentCreation({ experimentId, runtime }: { experimentId?: string; runtime: RuntimeReadiness | null }) {
  const [ideaSeed, setIdeaSeed] = useState("");
  const [revisionText, setRevisionText] = useState("");
  const [draft, setDraft] = useState(false);
  const [stage, setStage] = useState<Snapshot["stage"]>();
  const [stageStatus, setStageStatus] = useState<Snapshot["stage_status"]>();
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [proposalHistory, setProposalHistory] = useState<ProposalRevision[]>([]);
  const [mode, setMode] = useState<Mode>("USER_SEEDED_REFINEMENT");
  const [id, setId] = useState(experimentId ?? "");
  const [state, setState] = useState<ServerState | null>(null);
  const [busy, setBusy] = useState(experimentId ? "Loading saved experiment…" : "");
  const [message, setMessage] = useState("");
  const [statusUnavailable, setStatusUnavailable] = useState(false);
  const [createUncertain, setCreateUncertain] = useState(false);
  const [retrySafe, setRetrySafe] = useState(false);
  const [pollRevision, setPollRevision] = useState(0);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateChoice, setCandidateChoice] = useState("");
  const [selectionReason, setSelectionReason] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [pendingSelection, setPendingSelection] = useState<SelectionCommand | null>(null);
  const [pendingDraft, setPendingDraft] = useState<{ path: string; payload: object; action: "revise" | "regenerate" | "start" } | null>(null);
  const [runId, setRunId] = useState("");
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [adviceSource, setAdviceSource] = useState<Snapshot["advice_source"]>(null);
  const [acceptedBrief, setAcceptedBrief] = useState<Snapshot["accepted_brief"]>(null);
  const [relationship, setRelationship] = useState<Relationship | "">("");
  const [intentRationale, setIntentRationale] = useState("");
  const [intentConfirmed, setIntentConfirmed] = useState(false);
  const [pendingAcceptance, setPendingAcceptance] = useState<AcceptanceCommand | null>(null);
  const [returnAvailable, setReturnAvailable] = useState<ReturnAvailable | null>(null);
  const [pendingReturn, setPendingReturn] = useState<ReturnCommand | null>(null);
  const [returnReview, setReturnReview] = useState<ReturnReview | null>(null);
  const [liveConfirmed, setLiveConfirmed] = useState(false);
  const createPayload = useRef<components["schemas"]["CreateExperimentRequest"] | null>(null);
  const pendingIdeaCommand = useRef<{ path: string; payload: object } | null>(null);
  const discoverKey = useRef("");
  const refineKey = useRef("");

  const apply = useCallback((saved: Snapshot) => {
    setId(saved.experiment_id); setMode(saved.mode); setState(saved.state);
    setIdeaSeed(saved.idea_seed ?? ""); setDraft(saved.draft === true);
    setStage(saved.stage); setStageStatus(saved.stage_status); setBlockedReason(saved.blocked_reason ?? null);
    setProposalHistory(saved.proposal_history ?? []);
    setCandidates(saved.candidates ?? []); setSelectedCandidateId(saved.selected_candidate_artifact_id ?? "");
    if (saved.draft !== true) { sessionStorage.removeItem(draftCommandKey(saved.experiment_id)); setPendingDraft(null); }
    else {
      try { setPendingDraft(JSON.parse(sessionStorage.getItem(draftCommandKey(saved.experiment_id)) ?? "null")); }
      catch { sessionStorage.removeItem(draftCommandKey(saved.experiment_id)); setPendingDraft(null); }
    }
    const selection = pendingCommand<SelectionCommand>(saved.experiment_id, "select");
    if (selection && saved.selected_candidate_artifact_id === selection.candidate_artifact_id && saved.state !== "AWAITING_SELECTION") {
      sessionStorage.removeItem(commandKey(saved.experiment_id, "select")); setPendingSelection(null);
    } else {
      setPendingSelection(selection);
      if (selection) { setCandidateChoice(selection.candidate_artifact_id); setSelectionReason(selection.reason); }
    }
    setRunId(saved.latest_run_id ?? ""); setAdvice(saved.advice); setAdviceSource(saved.advice_source);
    setAcceptedBrief(saved.accepted_brief); setRetrySafe(saved.retry_safe === true);
    const returned = saved.return_context ?? saved.return_available ?? null;
    setReturnAvailable(returned);
    setReturnReview(saved.return_review ?? null);
    const returnCommand = pendingCommand<ReturnCommand>(saved.experiment_id, "return");
    const returnedCycleConfirmed = saved.cycle_purpose === "SAME_INTENT_RETURN" &&
      returned?.verdict_id === returnCommand?.verdict_id;
    if (returnCommand && (returnedCycleConfirmed || (!returned || returned.verdict_id !== returnCommand.verdict_id) && saved.state === "AWAITING_REFINEMENT")) {
      sessionStorage.removeItem(commandKey(saved.experiment_id, "return")); setPendingReturn(null);
    } else setPendingReturn(returnCommand);
    if (saved.state === "IDEA_ACCEPTED") {
      sessionStorage.removeItem(commandKey(saved.experiment_id, "accept")); setPendingAcceptance(null);
    } else {
      const acceptance = pendingCommand<AcceptanceCommand>(saved.experiment_id, "accept");
      setPendingAcceptance(acceptance);
      if (acceptance) {
        setRelationship(acceptance.intent_relationship); setIntentRationale(acceptance.intent_rationale);
        setIntentConfirmed(true);
      }
    }
    if (saved.stage_status === "RUNNING" || running(saved.state)) setPollRevision((revision) => revision + 1);
    setBusy(""); setStatusUnavailable(false);
    if (saved.retry_safe && failed(saved.state)) {
      const action = saved.state === "DISCOVERY_FAILED" ? "discover" : "refine";
      const key = action === "discover" ? discoverKey : refineKey;
      if (key.current || sessionStorage.getItem(runKey(saved.experiment_id, action))) {
        key.current = crypto.randomUUID();
        sessionStorage.setItem(runKey(saved.experiment_id, action), key.current);
      }
    }
  }, []);
  const load = useCallback(async (experiment: string, preserveMessage = false) => {
    try {
      const response = await fetch(`/api/operator/experiments/${encodeURIComponent(experiment)}`, { cache: "no-store" });
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error("STATUS_UNAVAILABLE");
      apply(await response.json() as Snapshot);
      if (!preserveMessage) setMessage("");
    } catch {
      setBusy(""); setStatusUnavailable(true);
      setMessage("Saved status is unavailable. No new run will start until the server confirms its state.");
    }
  }, [apply]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      if (experimentId) { void load(experimentId); return; }
      try {
        const draft = sessionStorage.getItem(draftKey);
        if (draft) {
          const pending = JSON.parse(draft) as { ideaSeed: string; payload: components["schemas"]["CreateExperimentRequest"]; path: string };
          setIdeaSeed(pending.ideaSeed); createPayload.current = pending.payload;
          pendingIdeaCommand.current = { path: pending.path, payload: pending.payload };
          setCreateUncertain(true); setMessage("Creation status is unknown. Retry the same command to recover it.");
        }
      } catch { sessionStorage.removeItem(draftKey); }
    });
    return () => { active = false; };
  }, [experimentId, load]);
  useEffect(() => {
    if (!id || !(stageStatus === "RUNNING" || running(state))) return;
    const timer = window.setTimeout(() => void load(id), 3000);
    return () => window.clearTimeout(timer);
  }, [id, state, stageStatus, pollRevision, load]);

  const start = async (event?: FormEvent<HTMLFormElement>, generate = false) => {
    event?.preventDefault();
    if (!generate && !ideaSeed.trim() && !createPayload.current) { setMessage("Enter an idea or generate one first."); return; }
    if (!runtime?.ready) { setMessage("The runtime is unavailable. Refresh after it is configured."); return; }
    if (runtime.provider_mode === "live" && !liveConfirmed) { setMessage("Confirm the live call before continuing."); return; }
    const path = generate ? "/api/operator/ideas/generate" : "/api/operator/experiments";
    if (!createPayload.current) {
      const payload = generate ? { command_key: crypto.randomUUID() } : createBody(ideaSeed, crypto.randomUUID());
      createPayload.current = payload;
      pendingIdeaCommand.current = { path, payload };
      sessionStorage.setItem(draftKey, JSON.stringify({ ideaSeed, path, payload }));
    }
    setBusy(generate ? "Generating ideas…" : "Starting experiment…"); setMessage("");
    try {
      const command = pendingIdeaCommand.current;
      if (!command) throw new Error("COMMAND_UNAVAILABLE");
      const result = await post(command.path, command.payload) as Snapshot;
      if (typeof result.experiment_id !== "string" || !result.state) throw new Error("CREATE_UNCONFIRMED");
      sessionStorage.removeItem(draftKey); createPayload.current = null; pendingIdeaCommand.current = null; setCreateUncertain(false);
      apply(result);
      window.history.replaceState(null, "", `/experiments/${encodeURIComponent(result.experiment_id)}`);
    } catch (error) {
      setBusy("");
      if (error instanceof Error && /^(FIELD:|OPERATOR_PROFILE_REQUIRED|INTAKE_BUDGET_REQUIRED|LIVE_CONFIG_REQUIRED|IDEA_REQUIRED)/.test(error.message)) {
        createPayload.current = null; pendingIdeaCommand.current = null; sessionStorage.removeItem(draftKey); setCreateUncertain(false);
      } else setCreateUncertain(true);
      setMessage(failure(error, generate ? "Idea generation" : "Experiment start"));
    }
  };
  const sendDraft = async (action: "revise" | "regenerate" | "start") => {
    const safeDiscoveryRetry = action === "regenerate" && state === "DISCOVERY_FAILED" && retrySafe;
    if (!id || !draft || !(stageStatus === "WAITING_FOR_INPUT" || safeDiscoveryRetry || pendingDraft) ||
      statusUnavailable || !runtime?.ready) return;
    if (runtime.provider_mode === "live" && !liveConfirmed) { setMessage("Confirm the live call before continuing."); return; }
    const text = revisionText;
    const command = pendingDraft ?? (() => {
      const key = crypto.randomUUID();
      if (action === "revise") return { action, path: `/api/operator/ideas/${encodeURIComponent(id)}/revisions`,
        payload: { candidate_artifact_id: candidateChoice, idea_seed: text, command_key: key } };
      if (action === "regenerate") return { action, path: `/api/operator/ideas/${encodeURIComponent(id)}/generate`,
        payload: { candidate_artifact_id: candidateChoice || undefined, command_key: key } };
      return { action, path: `/api/operator/ideas/${encodeURIComponent(id)}/start`,
        payload: { candidate_artifact_id: candidateChoice, command_key: key } };
    })();
    if (!pendingDraft && ((action !== "regenerate" && !candidateChoice) || (action === "revise" && !text.trim()))) return;
    sessionStorage.setItem(draftCommandKey(id), JSON.stringify(command)); setPendingDraft(command);
    setBusy(action === "revise" ? "Saving revision…" : action === "regenerate" ? "Generating new proposals…" : "Starting experiment…");
    setMessage("");
    try {
      const result = await post(command.path, command.payload) as Snapshot;
      if (result.experiment_id !== id || !result.state) throw new Error("COMMAND_UNCONFIRMED");
      sessionStorage.removeItem(draftCommandKey(id)); setPendingDraft(null);
      apply(result);
      if (action === "revise") {
        const revision = result.proposal_history?.at(-1);
        if (revision?.origin === "OPERATOR_EDIT") setCandidateChoice(revision.artifact_id);
      } else if (action === "regenerate") { setCandidateChoice(""); setRevisionText(""); }
    } catch (error) { setBusy(""); setMessage(failure(error, "Idea command")); await load(id, true); }
  };
  const run = async (action: "discover" | "refine") => {
    if (!id || !runtime?.ready) return;
    if (runtime.provider_mode === "live" && !liveConfirmed) { setMessage("Confirm the live call before continuing."); return; }
    const key = action === "discover" ? discoverKey : refineKey;
    key.current ||= sessionStorage.getItem(runKey(id, action)) || crypto.randomUUID();
    sessionStorage.setItem(runKey(id, action), key.current);
    setBusy(action === "discover" ? "Discovering directions…" : "Refining your idea…"); setMessage("");
    try {
      const result = await post(`/api/operator/experiments/${encodeURIComponent(id)}/${action}`, { idempotency_key: key.current });
      if (action === "discover") {
        if (result.state !== "AWAITING_SELECTION" || !Array.isArray(result.candidates) || result.candidates.length < 3 || result.candidates.length > 5) throw new Error("DISCOVERY_UNCONFIRMED");
        setCandidates(result.candidates); setState("AWAITING_SELECTION");
      } else {
        if (result.state !== "AWAITING_REVIEW" || !result.run_id || !result.advice) throw new Error("REFINEMENT_UNCONFIRMED");
        setRunId(result.run_id); setAdvice(result.advice); setAdviceSource(result.advice_source ?? null); setState("AWAITING_REVIEW");
      }
      setBusy(""); setRetrySafe(false);
      await load(id);
    } catch (error) {
      setMessage(failure(error, action === "discover" ? "Discovery" : "Refinement"));
      await load(id);
    }
  };
  const select = async () => {
    if (!id || statusUnavailable) return;
    const payload = pendingSelection ?? (candidateChoice && selectionReason.trim() ? {
      candidate_artifact_id: candidateChoice, reason: selectionReason.trim(), command_key: crypto.randomUUID(),
    } : null);
    if (!payload) return;
    if (!pendingSelection) {
      sessionStorage.setItem(commandKey(id, "select"), JSON.stringify(payload));
      setPendingSelection(payload);
    }
    setBusy("Saving selection…"); setMessage("");
    try {
      const result = await post(`/api/operator/experiments/${encodeURIComponent(id)}/select`, payload);
      if (result.state !== "AWAITING_REFINEMENT" || result.experiment_id !== id || !result.selection_id) throw new Error("SELECTION_UNCONFIRMED");
      sessionStorage.removeItem(commandKey(id, "select")); setPendingSelection(null);
      setSelectedCandidateId(payload.candidate_artifact_id); setState("AWAITING_REFINEMENT"); setBusy("");
    } catch (error) { setBusy(""); setMessage(failure(error, "Selection")); await load(id); }
  };
  const startReturn = async () => {
    if (!id || !returnAvailable || statusUnavailable) return;
    const payload: ReturnCommand = pendingReturn ?? {
      verdict_id: returnAvailable.verdict_id,
      feedback: { artifact_id: returnAvailable.feedback.artifact_id, kind: "RESEARCH_FEEDBACK_BRIEF",
        version: returnAvailable.feedback.version, content_hash: returnAvailable.feedback.content_hash,
        role: "RESEARCH_FEEDBACK" },
      command_key: crypto.randomUUID(),
    };
    if (!pendingReturn) {
      sessionStorage.setItem(commandKey(id, "return"), JSON.stringify(payload));
      setPendingReturn(payload);
    }
    setBusy("Starting refinement from committed feedback…"); setMessage("");
    try {
      const result = await post(`/api/operator/experiments/${encodeURIComponent(id)}/returns/refine`, payload);
      if (result.state !== "AWAITING_REFINEMENT" || result.experiment_id !== id || !result.cycle_id) throw new Error("RETURN_UNCONFIRMED");
      sessionStorage.removeItem(commandKey(id, "return")); setPendingReturn(null);
      setState("AWAITING_REFINEMENT"); setBusy("");
    } catch (error) { setBusy(""); setMessage(failure(error, "Return refinement")); await load(id, true); }
  };
  const accept = async () => {
    if (!id || !runId || !advice || statusUnavailable || advice.material_pivot || advice.intent_relationship === "MATERIAL_PIVOT" || advice.intent_relationship === "UNRELATED") return;
    const payload: AcceptanceCommand | null = pendingAcceptance ?? (intentConfirmed && intentRationale.trim() && relationship && relationship !== "MATERIAL_PIVOT" && relationship !== "UNRELATED" ? {
      run_id: runId, command_key: crypto.randomUUID(), intent_relationship: relationship,
      intent_rationale: intentRationale.trim(), intent_confirmed: true,
    } : null);
    if (!payload || payload.run_id !== runId) return;
    if (!pendingAcceptance) {
      sessionStorage.setItem(commandKey(id, "accept"), JSON.stringify(payload));
      setPendingAcceptance(payload);
    }
    setBusy("Saving accepted idea…"); setMessage("");
    try {
      const result = await post(`/api/operator/experiments/${encodeURIComponent(id)}/accept`, payload);
      if (result.state !== "IDEA_ACCEPTED" || result.experiment_id !== id || !result.idea_brief_artifact_id) throw new Error("ACCEPT_UNCONFIRMED");
      sessionStorage.removeItem(commandKey(id, "accept")); setPendingAcceptance(null);
      setAcceptedBrief(advice); setState("IDEA_ACCEPTED"); setBusy("");
    } catch (error) { setBusy(""); setMessage(failure(error, "Acceptance")); await load(id); }
  };
  const selectedCandidate = candidates.find((candidate) => candidate.artifact_id === selectedCandidateId);
  const blockedIntent = relationship === "MATERIAL_PIVOT" || relationship === "UNRELATED" || advice?.material_pivot || advice?.intent_relationship === "MATERIAL_PIVOT" || advice?.intent_relationship === "UNRELATED";
  const canRetry = retrySafe && failed(state) && !statusUnavailable;
  const canRefine = !draft && !statusUnavailable && !blockedReason && state === "AWAITING_REFINEMENT";
  const chosenDraft = candidates.find((candidate) => candidate.artifact_id === candidateChoice);
  const editChanged = !!chosenDraft && revisionText !== chosenDraft.hypothesis;

  return <div className="experiment-workspace">
    <header className="experiment-heading"><div><p className="eyebrow">Experiment studio / 01</p><h1>New experiment</h1><p>Bring an idea, or explore a few directions. You approve the final wording.</p></div>
      {state !== "IDEA_ACCEPTED" && <div className={runtime?.provider_mode === "live" && runtime.ready ? "experiment-runtime experiment-runtime--live" : "experiment-runtime"} role="note">
        {runtime?.ready && runtime.provider_mode === "live" ? <><strong>Live OpenAI mode</strong><p>Idea calls may incur a cost.</p><label><input type="checkbox" checked={liveConfirmed} onChange={(event) => setLiveConfirmed(event.target.checked)} /> I understand this may incur a cost</label></> :
          runtime?.ready && runtime.provider_mode === "fake" ? <><strong>Recorded demo · example output</strong><p>Prewritten Idea agent responses. No live research or Offer agent runs here.</p></> :
            <><strong>Runtime blocked</strong><p>No agent can start until the runtime is ready.</p></>}
      </div>}
    </header>
    <div className="experiment-step-track" aria-label="Creation stages"><span className={!id || draft ? "current" : "done"}>01 <b>Idea</b></span><span className={!draft && id && state !== "AWAITING_REVIEW" && state !== "IDEA_ACCEPTED" ? "current" : state === "AWAITING_REVIEW" || state === "IDEA_ACCEPTED" ? "done" : ""}>02 <b>Run</b></span><span className={state === "AWAITING_REVIEW" ? "current" : state === "IDEA_ACCEPTED" ? "done" : ""}>03 <b>Review</b></span></div>
    {(!id || !!ideaSeed) && <section className="experiment-form-panel" aria-labelledby="setup-heading">
      <div className="experiment-section-heading"><span>Starting point</span><h2 id="setup-heading">{id ? draft ? "Choose a direction" : "Your starting idea" : "What are you thinking about?"}</h2></div>
      {id ? <div className="experiment-saved-seed" title={`${draft ? "Proposal session" : "Experiment"} ${id}`}><div><span>{draft ? runtime?.provider_mode === "fake" ? "Exploring recorded examples" : "Exploring generated directions" : mode === "SYSTEM_DISCOVERY" ? "Selected direction" : "Original wording"}</span>{ideaSeed && <pre>{ideaSeed}</pre>}</div><p>{stageStatus === "RUNNING" ? "Agent running" : stageStatus === "BLOCKED" ? "Blocked" : stageStatus === "COMPLETE" ? "Complete" : "Waiting for input"}</p></div> :
        <form onSubmit={(event) => void start(event)} noValidate><label className="experiment-field experiment-field--wide"><span>Your idea <small>(optional)</small></span><textarea aria-label="Your idea" name="ideaSeed" value={ideaSeed} onChange={(event) => { setIdeaSeed(event.target.value); setMessage(""); }} rows={3} placeholder="Describe the problem or opportunity in a sentence…" disabled={!!busy || createUncertain} /><small>{runtime?.provider_mode === "fake" ? "Your exact wording is kept. Or start with recorded example directions." : "Your exact wording is kept. Or generate directions with the Idea agent."}</small></label>
          {message && <p className="experiment-error" role="alert">{message}</p>}<div className="experiment-action-row"><button type="submit" disabled={!runtime?.ready || !!busy}>{createUncertain ? "Retry start" : "Start experiment"} <span aria-hidden="true">↗</span></button><button type="button" className="experiment-secondary-action" disabled={!runtime?.ready || !!busy || createUncertain || !!ideaSeed.trim()} onClick={() => void start(undefined, true)}>Generate an idea</button></div></form>}
    </section>}
    {blockedReason && <p className="experiment-error" role="status">{blockedReason.replaceAll("_", " ")}</p>}
    {id && <section className="experiment-review" aria-live="polite" aria-labelledby="refinement-heading"><div className="experiment-section-heading"><span>{draft ? runtime?.provider_mode === "fake" ? "Recorded directions" : "Generated directions" : "Next step"}</span><h2 id="refinement-heading">{draft ? "Pick a direction" : state === "AWAITING_REVIEW" ? "Review the proposed change" : state === "IDEA_ACCEPTED" ? "Idea approved" : "Experiment progress"}</h2></div>
      {busy && <p role="status">{busy}</p>}
      {statusUnavailable && <button type="button" onClick={() => void load(id)}>Check status</button>}
      {!busy && (stageStatus === "RUNNING" || running(state)) && <div role="status"><p>{stage === "IDEA_DISCOVERY" ? "Idea discovery" : "Idea refinement"} in progress. Checking saved status.</p><button type="button" onClick={() => void load(id)}>Check status</button></div>}
      {!busy && canRetry && !draft && <button type="button" disabled={!runtime?.ready} onClick={() => void run(state === "DISCOVERY_FAILED" ? "discover" : "refine")}>Retry {state === "DISCOVERY_FAILED" ? "discovery" : "refinement"}</button>}
      {!busy && canRetry && draft && state === "DISCOVERY_FAILED" && <button type="button" disabled={!runtime?.ready} onClick={() => void sendDraft("regenerate")}>Retry discovery</button>}
      {!busy && !statusUnavailable && (state === "DISCOVERY_BLOCKED" || state === "REFINEMENT_BLOCKED" || failed(state) && !retrySafe) && <div role="status"><p>This attempt needs server resolution before another run can start.</p><button type="button" onClick={() => void load(id)}>Check status</button></div>}
      {message && <p className="experiment-error" role="alert">{message}</p>}
      {draft && stageStatus === "WAITING_FOR_INPUT" && !statusUnavailable && <div className="experiment-candidates"><p>{runtime?.provider_mode === "fake" ? "These are prewritten examples, not researched opportunities." : "These directions are hypotheses. Demand is unverified."} Pick one, change its wording if needed, then start.</p>
        <fieldset disabled={!!busy || !!pendingDraft}><legend className="visually-hidden">Choose a direction</legend>{candidates.map((candidate) => <label key={candidate.artifact_id} className="experiment-candidate"><input type="radio" name="candidate" checked={candidateChoice === candidate.artifact_id} onChange={() => { setCandidateChoice(candidate.artifact_id); setRevisionText(candidate.hypothesis); }} /><span><strong>{candidate.title}</strong><span>{candidate.hypothesis}</span></span></label>)}</fieldset>
        {candidateChoice && <div className="experiment-edit"><label className="experiment-field"><span>Change this direction <small>(optional)</small></span><textarea aria-label="Refine this proposal" value={revisionText} disabled={!!busy || !!pendingDraft} onChange={(event) => setRevisionText(event.target.value)} rows={2} /></label><p>{editChanged ? "Keep your edit first so Start uses your words." : "Starting uses the selected wording above."}</p></div>}
        {pendingDraft ? <><p>Confirmation is pending. Check saved status, then retry this exact command.</p><button type="button" disabled={!!busy} onClick={() => void sendDraft(pendingDraft.action)}>Retry {pendingDraft.action}</button></> : <div className="experiment-action-row"><button type="button" disabled={!candidateChoice || editChanged || !!busy} onClick={() => void sendDraft("start")}>Start experiment <span aria-hidden="true">↗</span></button>{candidateChoice && <button type="button" className="experiment-secondary-action" disabled={!editChanged || !revisionText.trim() || !!busy} onClick={() => void sendDraft("revise")}>Keep edited version</button>}<button type="button" className="experiment-text-action" disabled={!!busy} onClick={() => void sendDraft("regenerate")}>Try more directions</button></div>}
      </div>}
      {proposalHistory.length > 0 && <details className="experiment-history" aria-label="Proposal history"><summary>Earlier versions <span>{proposalHistory.length}</span></summary><p>Every generated direction and saved edit is kept here so you can trace how this idea changed.</p><ol>{proposalHistory.map((revision) => <li key={revision.artifact_id}><strong>v{revision.version} · {revision.origin === "OPERATOR_EDIT" ? "Your edit" : "Generated"}</strong><span>{revision.idea_seed ?? revision.hypothesis}</span></li>)}</ol></details>}
      {returnAvailable && <section className="experiment-return" aria-labelledby="return-heading"><div className="experiment-section-heading"><span>Research return</span><h3 id="return-heading">Research feedback return</h3></div>
        <p>Committed verdict: <strong>REFINE_SAME_IDEA</strong> · Research cycle: {returnAvailable.research_cycle_id}</p>
        <div className="experiment-return__grid"><div><h4>Committed feedback</h4><dl><div><dt>Feedback artifact</dt><dd>{returnAvailable.feedback.artifact_id} · v{returnAvailable.feedback.version}</dd></div><div><dt>Evidence</dt><dd>{returnAvailable.evidence.report_artifact_id} · {returnAvailable.evidence.recommendation_artifact_id}</dd></div></dl>
          {Object.entries(returnAvailable.feedback.payload).map(([field, value]) => <p key={field}><strong>{field.replaceAll("_", " ")}: </strong>{feedbackValue(value)}</p>)}
          <h4>Blocked or unverified</h4><ul>{returnAvailable.feedback.failed_dimensions.map((item) => <li key={item}>{item}</li>)}</ul></div>
          <div><h4>Prior accepted version</h4><BriefDetails brief={returnAvailable.prior_brief.payload} /><h4>Return lineage</h4><ol>{returnAvailable.return_lineage.map((lineage) => <li key={lineage.return_id}>Return {lineage.ordinal}: {lineage.from_cycle_id} → {lineage.to_cycle_id}</li>)}</ol></div></div>
        {state === "RETURN_REVIEW_REQUIRED" && !returnReview && (pendingReturn ? <><p>Return confirmation is pending. Retry the exact saved command after checking server status.</p><button type="button" disabled={!!busy || statusUnavailable} onClick={() => void startReturn()}>Retry return refinement</button></> : <button type="button" disabled={!!busy || statusUnavailable || !runtime?.ready} onClick={() => void startReturn()}>Start refinement from committed feedback</button>)}</section>}
      {state === "RETURN_REVIEW_REQUIRED" && returnReview && <section className="experiment-return experiment-return--review" aria-labelledby="return-review-heading" role="status"><div className="experiment-section-heading"><span>Operator decision</span><h3 id="return-review-heading">Operator review required</h3></div><p>{returnReviewMessage(returnReview.reason_code)}</p><p>Research cycle: {returnReview.research_cycle_id} · Reason: {returnReview.reason_code}</p></section>}
      {!draft && mode === "SYSTEM_DISCOVERY" && candidates.length >= 3 && candidates.length <= 5 && <div className="experiment-candidates"><p>{runtime?.provider_mode === "fake" ? "Recorded example directions; no demand has been tested." : "Directions are hypotheses; demand has not been tested."}</p>
        {state === "AWAITING_SELECTION" ? <><fieldset disabled={!!busy || !!pendingSelection}><legend>Choose one direction to refine</legend>{candidates.map((candidate) => <label key={candidate.artifact_id} className="experiment-candidate"><input type="radio" name="candidate" checked={candidateChoice === candidate.artifact_id} onChange={() => setCandidateChoice(candidate.artifact_id)} /><span><strong>{candidate.title}</strong><span>{candidate.hypothesis}</span></span></label>)}</fieldset>{pendingSelection ? <><p>Selection confirmation is pending. Retry the saved choice and reason with the same command.</p><p>Reason: {pendingSelection.reason}</p><button type="button" disabled={!!busy || statusUnavailable} onClick={() => void select()}>Retry selection</button></> : <><label className="experiment-field"><span>Why this direction?</span><textarea aria-label="Reason for selection" value={selectionReason} onChange={(event) => setSelectionReason(event.target.value)} rows={2} /></label><button type="button" disabled={!candidateChoice || !selectionReason.trim() || !!busy || statusUnavailable} onClick={() => void select()}>Select direction</button></>}</> :
          selectedCandidate && <p className="experiment-selected">Selected direction: <strong>{selectedCandidate.title}</strong></p>}</div>}
      {!busy && canRefine && <button type="button" disabled={!runtime?.ready} onClick={() => void run("refine")}>{returnAvailable ? "Refine returned idea" : mode === "SYSTEM_DISCOVERY" ? "Refine selected direction" : "Refine idea"}</button>}
      {advice && state === "AWAITING_REVIEW" && <div className="experiment-advice"><div className="experiment-advice__lead"><span className="eyebrow">{returnAvailable ? "Returned idea · awaiting approval" : adviceSource === "RECORDED_FAKE" ? "Recorded example · no live agent ran" : "Idea agent suggestion · awaiting approval"}</span><h3>{advice.title}</h3>{advice.core_intent !== advice.title && <p>{advice.core_intent}</p>}<small>This is suggested wording for your idea. It becomes the current version only if you approve it.</small></div><dl><div><dt>For</dt><dd>{advice.customer}</dd></div><div><dt>Problem</dt><dd>{advice.problem}</dd></div></dl>
        <details className="experiment-proposed-brief"><summary>Full suggested idea and open questions</summary><BriefDetails brief={advice} /><div className="experiment-uncertainties"><h4>Still unverified</h4><ul aria-label="Unknowns to test">{advice.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul><p>Source references: {advice.grounding_refs.join(" · ")}</p></div></details>
        <div className="experiment-intent"><div><h4>Approve this version?</h4><p>Suggested relationship: {relationshipLabels[advice.intent_relationship]}. Your classification decides whether it can be accepted.</p></div>{pendingAcceptance ? <><p>Acceptance confirmation is pending. Retry the exact saved review command.</p><p>Operator classification: {relationshipLabels[pendingAcceptance.intent_relationship]}</p><p>Reason: {pendingAcceptance.intent_rationale}</p><button type="button" disabled={!!busy || statusUnavailable || !!blockedIntent || pendingAcceptance.run_id !== runId} onClick={() => void accept()}>Retry acceptance</button></> : <><div className="experiment-intent__fields"><label className="experiment-field"><span>How does it relate to your idea?</span><select aria-label="Intent relationship" value={relationship} onChange={(event) => { setRelationship(event.target.value as Relationship); setIntentConfirmed(false); }}><option value="">Choose a relationship</option><option value="PRESERVES_CORE_INTENT">Preserves core intent</option><option value="CLARIFIES_CORE_INTENT">Clarifies core intent</option><option value="NARROWS_CORE_INTENT">Narrows core intent</option><option value="MATERIAL_PIVOT">Material pivot</option><option value="UNRELATED">Unrelated</option></select></label><label className="experiment-field"><span>Why?</span><textarea aria-label="Reason for classification" value={intentRationale} onChange={(event) => setIntentRationale(event.target.value)} rows={2} /></label></div><label className="experiment-confirm"><input type="checkbox" checked={intentConfirmed} disabled={!relationship || !!blockedIntent} onChange={(event) => setIntentConfirmed(event.target.checked)} /> I confirm this classification and approve accepting this idea</label></>}
        {blockedIntent && <p className="experiment-error">{relationship === "UNRELATED" || advice.intent_relationship === "UNRELATED" ? "An unrelated proposal cannot be accepted here." : "A material pivot cannot be accepted here; it requires a separate approval decision."}</p>}{!pendingAcceptance && <button type="button" disabled={!relationship || !intentConfirmed || !intentRationale.trim() || !!blockedIntent || !!busy || statusUnavailable} onClick={() => void accept()}>Accept and save idea</button>}</div></div>}
      {state === "IDEA_ACCEPTED" && <div className="experiment-success" role="status"><strong>Experiment ready</strong>{acceptedBrief && <><h3>{acceptedBrief.title}</h3><p>{acceptedBrief.core_intent}</p></>}{adviceSource === "RECORDED_FAKE" && <p>Accepted from a recorded example. No live agent ran.</p>}<p>The accepted idea is saved as the current version.</p><a href={`/experiments/${encodeURIComponent(id)}`}>View experiment <span aria-hidden="true">↗</span></a></div>}
    </section>}
  </div>;
}
