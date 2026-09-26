"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

type Mode = "USER_SEEDED_REFINEMENT" | "SYSTEM_DISCOVERY";
type Relationship = "PRESERVES_CORE_INTENT" | "CLARIFIES_CORE_INTENT" | "NARROWS_CORE_INTENT" | "MATERIAL_PIVOT" | "UNRELATED";
type Values = {
  name: string; ideaSeed: string; objective: string; targetCustomer: string;
  problem: string; geographies: string; commercialBoundaries: string;
  budgetUsd: string; evidenceDefinitions: string; capabilities: string;
  constraints: string; maxProjectHours: string; hoursPerWeek: string;
  concurrentProjects: string; currency: string; hourlyCost: string;
  minimumProjectPrice: string; minimumMarginRate: string;
  maximumDiscountRate: string; minimumDepositRate: string;
};
type Advice = {
  title: string; customer: string; problem: string; core_intent: string;
  material_pivot: boolean; intent_relationship: Relationship;
  grounding_refs: string[]; uncertainties: string[];
};
const relationshipLabels: Record<Relationship, string> = {
  PRESERVES_CORE_INTENT: "Preserves core intent",
  CLARIFIES_CORE_INTENT: "Clarifies core intent",
  NARROWS_CORE_INTENT: "Narrows core intent",
  MATERIAL_PIVOT: "Material pivot",
  UNRELATED: "Unrelated",
};
type Candidate = { artifact_id: string; title: string; hypothesis: string; demand_status: "UNVERIFIED"; uncertainties: string[] };
type SelectionCommand = { candidate_artifact_id: string; reason: string; command_key: string };
type AcceptanceCommand = { run_id: string; command_key: string; intent_relationship: Relationship;
  intent_rationale: string; intent_confirmed: true };
type ServerState = "AWAITING_DISCOVERY" | "DISCOVERY_IN_PROGRESS" | "DISCOVERY_FAILED" | "DISCOVERY_BLOCKED" |
  "AWAITING_SELECTION" | "AWAITING_REFINEMENT" | "REFINEMENT_IN_PROGRESS" | "REFINEMENT_FAILED" |
  "REFINEMENT_BLOCKED" | "AWAITING_REVIEW" | "IDEA_ACCEPTED";
type Snapshot = {
  experiment_id: string; name: string; mode: Mode; idea_seed: string | null; state: ServerState;
  brief: { objective: string; target_customer: string; problem: string; geographies: string[];
    commercial_boundaries: string; budget_usd: string; evidence_definitions: string[] };
  candidates: Candidate[]; selected_candidate_artifact_id: string | null; retry_safe: boolean;
  latest_run_id: string | null; advice: Advice | null;
  advice_source: "RECORDED_FAKE" | "OPENAI" | null;
  accepted_brief: Pick<Advice, "title" | "customer" | "problem" | "core_intent" | "material_pivot"> | null;
};
export type RuntimeReadiness = { provider_mode: "disabled" | "fake" | "live"; ready: boolean };

const draftKey = "experiment-create-pending";
const runKey = (experiment: string, action: "discover" | "refine") => `experiment-${experiment}-${action}-key`;
const commandKey = (experiment: string, action: "select" | "accept") => `experiment-${experiment}-${action}-pending`;
function pendingCommand<T>(experiment: string, action: "select" | "accept"): T | null {
  try { return JSON.parse(sessionStorage.getItem(commandKey(experiment, action)) ?? "null") as T | null; }
  catch { return null; }
}
const empty: Values = {
  name: "", ideaSeed: "", objective: "", targetCustomer: "", problem: "", geographies: "",
  commercialBoundaries: "", budgetUsd: "", evidenceDefinitions: "", capabilities: "",
  constraints: "", maxProjectHours: "", hoursPerWeek: "", concurrentProjects: "",
  currency: "", hourlyCost: "", minimumProjectPrice: "", minimumMarginRate: "",
  maximumDiscountRate: "", minimumDepositRate: "",
};
const fields: { key: keyof Values; label: string; hint?: string; tall?: boolean }[] = [
  { key: "name", label: "Experiment name" },
  { key: "ideaSeed", label: "Your idea", hint: "Your text is preserved exactly.", tall: true },
  { key: "objective", label: "Objective", tall: true },
  { key: "targetCustomer", label: "Target customer" },
  { key: "problem", label: "Problem hypothesis", tall: true },
  { key: "geographies", label: "Geographies", hint: "One per line." },
  { key: "commercialBoundaries", label: "Commercial boundaries", tall: true },
  { key: "budgetUsd", label: "Research budget (USD)" },
  { key: "evidenceDefinitions", label: "Evidence definitions", hint: "One signal per line.", tall: true },
  { key: "capabilities", label: "Capabilities", hint: "One per line.", tall: true },
  { key: "constraints", label: "Constraints", hint: "One per line.", tall: true },
  { key: "maxProjectHours", label: "Maximum project hours" },
  { key: "hoursPerWeek", label: "Hours per week" },
  { key: "concurrentProjects", label: "Concurrent projects" },
  { key: "hourlyCost", label: "Hourly cost" },
  { key: "minimumProjectPrice", label: "Minimum project price" },
  { key: "minimumMarginRate", label: "Minimum margin rate", hint: "Use a decimal such as 0.30." },
  { key: "maximumDiscountRate", label: "Maximum discount rate", hint: "Use a decimal such as 0.10." },
  { key: "minimumDepositRate", label: "Minimum deposit rate", hint: "Use a decimal such as 0.25." },
];
const positive = ["budgetUsd", "maxProjectHours", "hoursPerWeek", "concurrentProjects", "hourlyCost", "minimumProjectPrice"] as const;
const rates = ["minimumMarginRate", "maximumDiscountRate", "minimumDepositRate"] as const;
const split = (value: string) => value.split(/\n|,/).map((part) => part.trim()).filter(Boolean);
const running = (state: ServerState | null) => state === "DISCOVERY_IN_PROGRESS" || state === "REFINEMENT_IN_PROGRESS";
const failed = (state: ServerState | null) => state === "DISCOVERY_FAILED" || state === "REFINEMENT_FAILED";

function complete(values: Values, mode: Mode) {
  return Object.entries(values).every(([key, value]) => key === "ideaSeed" && mode === "SYSTEM_DISCOVERY" || value.trim()) &&
    ["geographies", "evidenceDefinitions", "capabilities", "constraints"].every((key) => split(values[key as keyof Values]).length > 0) &&
    positive.every((key) => Number.isFinite(Number(values[key])) && Number(values[key]) > 0) &&
    Number.isInteger(Number(values.concurrentProjects)) &&
    rates.every((key) => Number.isFinite(Number(values[key])) && Number(values[key]) >= 0 && Number(values[key]) <= 1);
}

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
  if (code.includes("UNRELATED")) return "An unrelated direction cannot be accepted here.";
  if (code.includes("MATERIAL_PIVOT")) return "A material pivot needs a separate approval decision.";
  return `${action} could not finish. Check the saved status before starting a new attempt.`;
}
function createBody(values: Values, mode: Mode, commandKey: string) {
  return {
    name: values.name.trim(), ...(mode === "USER_SEEDED_REFINEMENT" ? { idea_seed: values.ideaSeed } : {}),
    brief: { objective: values.objective.trim(), target_customer: values.targetCustomer.trim(),
      problem: values.problem.trim(), geographies: split(values.geographies),
      commercial_boundaries: values.commercialBoundaries.trim(), budget_usd: values.budgetUsd.trim(),
      evidence_definitions: split(values.evidenceDefinitions), launch_stage: "SHADOW" },
    operator_profile: { capabilities: split(values.capabilities), constraints: split(values.constraints),
      delivery: { max_project_hours: values.maxProjectHours.trim(), hours_per_week: values.hoursPerWeek.trim(),
        concurrent_projects: Number(values.concurrentProjects) },
      commercial: { currency: values.currency, hourly_cost: values.hourlyCost.trim(),
        minimum_project_price: values.minimumProjectPrice.trim(), minimum_margin_rate: values.minimumMarginRate.trim(),
        maximum_discount_rate: values.maximumDiscountRate.trim(), minimum_deposit_rate: values.minimumDepositRate.trim() } },
    command_key: commandKey,
  };
}

export function ExperimentCreation({ experimentId, runtime }: { experimentId?: string; runtime: RuntimeReadiness | null }) {
  const [values, setValues] = useState<Values>(empty);
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
  const [runId, setRunId] = useState("");
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [adviceSource, setAdviceSource] = useState<Snapshot["advice_source"]>(null);
  const [acceptedBrief, setAcceptedBrief] = useState<Snapshot["accepted_brief"]>(null);
  const [relationship, setRelationship] = useState<Relationship | "">("");
  const [intentRationale, setIntentRationale] = useState("");
  const [intentConfirmed, setIntentConfirmed] = useState(false);
  const [pendingAcceptance, setPendingAcceptance] = useState<AcceptanceCommand | null>(null);
  const [liveConfirmed, setLiveConfirmed] = useState(false);
  const createPayload = useRef<ReturnType<typeof createBody> | null>(null);
  const discoverKey = useRef("");
  const refineKey = useRef("");

  const apply = useCallback((saved: Snapshot) => {
    setId(saved.experiment_id); setMode(saved.mode); setState(saved.state);
    setValues((current) => ({ ...current, name: saved.name, ideaSeed: saved.idea_seed ?? "",
      objective: saved.brief.objective, targetCustomer: saved.brief.target_customer,
      problem: saved.brief.problem, geographies: saved.brief.geographies.join("\n"),
      commercialBoundaries: saved.brief.commercial_boundaries, budgetUsd: saved.brief.budget_usd,
      evidenceDefinitions: saved.brief.evidence_definitions.join("\n") }));
    setCandidates(saved.candidates ?? []); setSelectedCandidateId(saved.selected_candidate_artifact_id ?? "");
    const selection = pendingCommand<SelectionCommand>(saved.experiment_id, "select");
    if (selection && saved.selected_candidate_artifact_id === selection.candidate_artifact_id && saved.state !== "AWAITING_SELECTION") {
      sessionStorage.removeItem(commandKey(saved.experiment_id, "select")); setPendingSelection(null);
    } else {
      setPendingSelection(selection);
      if (selection) { setCandidateChoice(selection.candidate_artifact_id); setSelectionReason(selection.reason); }
    }
    setRunId(saved.latest_run_id ?? ""); setAdvice(saved.advice); setAdviceSource(saved.advice_source);
    setAcceptedBrief(saved.accepted_brief); setRetrySafe(saved.retry_safe === true);
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
    if (running(saved.state)) setPollRevision((revision) => revision + 1);
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
  const load = useCallback(async (experiment: string) => {
    try {
      const response = await fetch(`/api/operator/experiments/${encodeURIComponent(experiment)}`, { cache: "no-store" });
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error("STATUS_UNAVAILABLE");
      apply(await response.json() as Snapshot);
      setMessage("");
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
          const pending = JSON.parse(draft) as { values: Values; mode: Mode; payload: ReturnType<typeof createBody> };
          setValues(pending.values); setMode(pending.mode); createPayload.current = pending.payload;
          setCreateUncertain(true); setMessage("Creation status is unknown. Retry the same command to recover it.");
        }
      } catch { sessionStorage.removeItem(draftKey); }
    });
    return () => { active = false; };
  }, [experimentId, load]);
  useEffect(() => {
    if (!id || !running(state)) return;
    const timer = window.setTimeout(() => void load(id), 3000);
    return () => window.clearTimeout(timer);
  }, [id, state, pollRevision, load]);

  const change = (key: keyof Values, value: string) => {
    setValues((current) => ({ ...current, [key]: value })); setMessage("");
  };
  const create = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!createPayload.current && !complete(values, mode)) {
      setMessage("Complete the experiment bounds with valid amounts and rates before continuing."); return;
    }
    if (!runtime?.ready) { setMessage("The runtime is unavailable. Refresh after it is configured."); return; }
    if (!createPayload.current) {
      createPayload.current = createBody(values, mode, crypto.randomUUID());
      sessionStorage.setItem(draftKey, JSON.stringify({ values, mode, payload: createPayload.current }));
    }
    setBusy("Creating experiment…"); setMessage("");
    try {
      const result = await post("/api/operator/experiments", createPayload.current);
      if (typeof result.experiment_id !== "string" || !["AWAITING_DISCOVERY", "AWAITING_REFINEMENT"].includes(result.state)) throw new Error("CREATE_UNCONFIRMED");
      sessionStorage.removeItem(draftKey); createPayload.current = null; setCreateUncertain(false);
      setId(result.experiment_id); setState(result.state); setBusy("");
      window.history.replaceState(null, "", `/experiments/${encodeURIComponent(result.experiment_id)}`);
    } catch (error) {
      setBusy("");
      if (error instanceof Error && error.message.startsWith("FIELD:")) {
        createPayload.current = null; sessionStorage.removeItem(draftKey); setCreateUncertain(false);
      } else setCreateUncertain(true);
      setMessage(failure(error, "Creation"));
    }
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
  const canRefine = !statusUnavailable && state === "AWAITING_REFINEMENT" && (mode === "USER_SEEDED_REFINEMENT" || !!selectedCandidateId);

  return <div className="experiment-workspace">
    <div className="experiment-heading"><p className="eyebrow">Experiment / idea origin</p><h1>Start with a direction.<br /><em>Make it testable.</em></h1><p>Define the boundaries, review the proposed direction, and explicitly accept the result.</p></div>
    <div className="experiment-step-track" aria-label="Creation stages"><span className={!id ? "current" : "done"}>01 · Define</span><span className={state === "AWAITING_REVIEW" || state === "IDEA_ACCEPTED" ? "done" : id ? "current" : ""}>02 · Discover / refine</span><span className={state === "AWAITING_REVIEW" ? "current" : state === "IDEA_ACCEPTED" ? "done" : ""}>03 · Review</span></div>
    {state !== "IDEA_ACCEPTED" && <div className={runtime?.provider_mode === "live" && runtime.ready ? "experiment-runtime experiment-runtime--live" : "experiment-runtime"} role="note">
      {runtime?.ready && runtime.provider_mode === "live" ? <><strong>Live OpenAI calls</strong><p>Discovery or refinement may incur a cost under the research budget. Confirm before starting either call.</p><label><input type="checkbox" checked={liveConfirmed} onChange={(event) => setLiveConfirmed(event.target.checked)} /> I understand this may incur a cost</label></> :
        runtime?.ready && runtime.provider_mode === "fake" ? <><strong>Recorded demo mode</strong><p>Discovery and refinement use synthetic recorded results. No live OpenAI call is made.</p></> :
          <><strong>Runtime unavailable</strong><p>The server has not confirmed an available runtime.</p></>}
    </div>}
    <div className="experiment-columns"><section className="experiment-form-panel" aria-labelledby="setup-heading">
      <div className="experiment-section-heading"><span>01 / Setup</span><h2 id="setup-heading">Your starting point</h2></div>
      {id ? <div className="experiment-saved-seed"><span className="eyebrow">{mode === "SYSTEM_DISCOVERY" ? "System discovery" : "Original idea · saved exactly"}</span>{mode === "USER_SEEDED_REFINEMENT" && <pre>{values.ideaSeed}</pre>}<p>Experiment ID: {id}</p></div> :
        <form onSubmit={(event) => void create(event)} noValidate><fieldset className="experiment-fieldset" disabled={!!busy || createUncertain}>
          <legend className="experiment-mode-label">Idea origin</legend><div className="experiment-mode-options"><label><input type="radio" name="mode" checked={mode === "USER_SEEDED_REFINEMENT"} onChange={() => setMode("USER_SEEDED_REFINEMENT")} /> Refine my idea</label><label><input type="radio" name="mode" checked={mode === "SYSTEM_DISCOVERY"} onChange={() => setMode("SYSTEM_DISCOVERY")} /> System discovery</label></div>
          <div className="experiment-fields">{fields.filter(({ key }) => key !== "ideaSeed" || mode === "USER_SEEDED_REFINEMENT").map(({ key, label, hint, tall }) => <label className={tall ? "experiment-field experiment-field--wide" : "experiment-field"} key={key}><span>{label}</span>
            {tall ? <textarea aria-label={label} name={key} value={values[key]} onChange={(event) => change(key, event.target.value)} rows={key === "ideaSeed" ? 4 : 2} /> :
              <input aria-label={label} name={key} type="text" inputMode={positive.includes(key as typeof positive[number]) || rates.includes(key as typeof rates[number]) ? "decimal" : "text"} value={values[key]} onChange={(event) => change(key, event.target.value)} />}{hint && <small>{hint}</small>}</label>)}
            <label className="experiment-field"><span>Currency</span><select name="currency" value={values.currency} onChange={(event) => change("currency", event.target.value)}><option value="">Select currency</option><option value="ILS">ILS</option><option value="USD">USD</option></select></label>
          </div></fieldset>{message && <p className="experiment-error" role="alert">{message}</p>}<div className="experiment-action-row"><button type={createUncertain ? "button" : "submit"} disabled={!runtime?.ready || !!busy} onClick={createUncertain ? () => void create() : undefined}>{createUncertain ? "Retry creation" : "Create experiment"} <span aria-hidden="true">↗</span></button><span>First stage: SHADOW</span></div></form>}
    </section><aside className="experiment-preview" aria-label="Experiment preview"><div className="experiment-section-heading"><span>Live preview</span><h2>Mission brief</h2></div>
      <dl><div><dt>Customer</dt><dd>{values.targetCustomer || "Awaiting target"}</dd></div><div><dt>Problem</dt><dd>{values.problem || "Awaiting hypothesis"}</dd></div><div><dt>Geography</dt><dd>{values.geographies || "Awaiting location"}</dd></div><div><dt>Research budget</dt><dd>{values.budgetUsd ? `$${values.budgetUsd}` : "Awaiting budget"}</dd></div><div><dt>First stage</dt><dd>SHADOW</dd></div></dl>
      {mode === "USER_SEEDED_REFINEMENT" && <div className="experiment-seed-preview"><span className="eyebrow">Original text</span><pre data-testid="seed-preview">{values.ideaSeed}</pre></div>}
      <p className="experiment-preview-note">{mode === "SYSTEM_DISCOVERY" ? "Discovery suggestions are hypotheses. Demand is unverified until research tests it." : "A refined idea becomes current only after explicit operator acceptance."}</p>
    </aside></div>
    {id && <section className="experiment-review" aria-live="polite" aria-labelledby="refinement-heading"><div className="experiment-section-heading"><span>02 / Decision</span><h2 id="refinement-heading">Idea review</h2></div>
      {busy && <p role="status">{busy}</p>}
      {statusUnavailable && <button type="button" onClick={() => void load(id)}>Check status</button>}
      {!busy && running(state) && <div role="status"><p>{state === "DISCOVERY_IN_PROGRESS" ? "Discovery in progress." : "Refinement in progress."} Checking server status before another attempt.</p><button type="button" onClick={() => void load(id)}>Check status</button></div>}
      {!busy && !statusUnavailable && state === "AWAITING_DISCOVERY" && <button type="button" disabled={!runtime?.ready} onClick={() => void run("discover")}>Discover directions</button>}
      {!busy && canRetry && <button type="button" disabled={!runtime?.ready} onClick={() => void run(state === "DISCOVERY_FAILED" ? "discover" : "refine")}>Retry {state === "DISCOVERY_FAILED" ? "discovery" : "refinement"}</button>}
      {!busy && !statusUnavailable && (state === "DISCOVERY_BLOCKED" || state === "REFINEMENT_BLOCKED" || failed(state) && !retrySafe) && <div role="status"><p>This attempt needs server resolution before another run can start.</p><button type="button" onClick={() => void load(id)}>Check status</button></div>}
      {message && <p className="experiment-error" role="alert">{message}</p>}
      {mode === "SYSTEM_DISCOVERY" && candidates.length >= 3 && candidates.length <= 5 && <div className="experiment-candidates"><p>These are grounded hypotheses; demand is unverified.</p>
        {state === "AWAITING_SELECTION" ? <><fieldset disabled={!!busy || !!pendingSelection}><legend>Choose one direction to refine</legend>{candidates.map((candidate) => <label key={candidate.artifact_id} className="experiment-candidate"><input type="radio" name="candidate" checked={candidateChoice === candidate.artifact_id} onChange={() => setCandidateChoice(candidate.artifact_id)} /><span><strong>{candidate.title}</strong><span>{candidate.hypothesis}</span><small>{candidate.demand_status === "UNVERIFIED" ? "Unverified demand" : "Demand status unknown"} · Grounded in your operator profile · Unknowns: {candidate.uncertainties.join(" · ")}</small></span></label>)}</fieldset>{pendingSelection ? <><p>Selection confirmation is pending. Retry the saved choice and reason with the same command.</p><p>Reason: {pendingSelection.reason}</p><button type="button" disabled={!!busy || statusUnavailable} onClick={() => void select()}>Retry selection</button></> : <><label className="experiment-field"><span>Reason for selection</span><textarea aria-label="Reason for selection" value={selectionReason} onChange={(event) => setSelectionReason(event.target.value)} rows={2} /></label><button type="button" disabled={!candidateChoice || !selectionReason.trim() || !!busy || statusUnavailable} onClick={() => void select()}>Select direction</button></>}</> :
          selectedCandidate && <p className="experiment-selected">Selected direction: <strong>{selectedCandidate.title}</strong></p>}</div>}
      {!busy && canRefine && <button type="button" disabled={!runtime?.ready} onClick={() => void run("refine")}>{mode === "SYSTEM_DISCOVERY" ? "Refine selected direction" : "Refine idea"}</button>}
      {advice && state === "AWAITING_REVIEW" && <div className="experiment-advice"><div className="experiment-advice__lead"><span className="eyebrow">{adviceSource === "RECORDED_FAKE" ? "Recorded demo advice" : "Proposed direction · unaccepted advice"}</span><h3>{advice.title}</h3><p>{advice.core_intent}</p></div><dl><div><dt>Customer</dt><dd>{advice.customer}</dd></div><div><dt>Problem</dt><dd>{advice.problem}</dd></div><div><dt>Grounded in</dt><dd>{advice.grounding_refs.join(" · ")}</dd></div></dl><div className="experiment-uncertainties"><h4>Starting assumptions <small>supplied by you</small></h4><ul aria-label="Starting assumptions"><li>Customer: <span>{values.targetCustomer}</span></li><li>Problem: <span>{values.problem}</span></li><li>Objective: <span>{values.objective}</span></li></ul><h4>Unknowns to test <small>from refinement advice</small></h4><ul aria-label="Unknowns to test">{advice.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div className="experiment-intent"><p>Model suggestion: {relationshipLabels[advice.intent_relationship]}</p>{pendingAcceptance ? <><p>Acceptance confirmation is pending. Retry the exact saved review command.</p><p>Operator classification: {relationshipLabels[pendingAcceptance.intent_relationship]}</p><p>Reason: {pendingAcceptance.intent_rationale}</p><button type="button" disabled={!!busy || statusUnavailable || !!blockedIntent || pendingAcceptance.run_id !== runId} onClick={() => void accept()}>Retry acceptance</button></> : <><label className="experiment-field"><span>Intent relationship</span><select aria-label="Intent relationship" value={relationship} onChange={(event) => { setRelationship(event.target.value as Relationship); setIntentConfirmed(false); }}><option value="">Classify the proposal</option><option value="PRESERVES_CORE_INTENT">Preserves core intent</option><option value="CLARIFIES_CORE_INTENT">Clarifies core intent</option><option value="NARROWS_CORE_INTENT">Narrows core intent</option><option value="MATERIAL_PIVOT">Material pivot</option><option value="UNRELATED">Unrelated</option></select></label><p>Compare the proposal with the original seed or selected discovery direction. The model suggestion is advisory; your classification and confirmation control acceptance.</p><label className="experiment-field"><span>Reason for classification</span><textarea aria-label="Reason for classification" value={intentRationale} onChange={(event) => setIntentRationale(event.target.value)} rows={2} /></label><label><input type="checkbox" checked={intentConfirmed} disabled={!relationship || !!blockedIntent} onChange={(event) => setIntentConfirmed(event.target.checked)} /> I confirm this classification and approve accepting this idea</label></>}
        {blockedIntent && <p className="experiment-error">{relationship === "UNRELATED" || advice.intent_relationship === "UNRELATED" ? "An unrelated proposal cannot be accepted here." : "A material pivot cannot be accepted here; it requires a separate approval decision."}</p>}</div>
        {!pendingAcceptance && <button type="button" disabled={!relationship || !intentConfirmed || !intentRationale.trim() || !!blockedIntent || !!busy || statusUnavailable} onClick={() => void accept()}>Accept and save idea</button>}</div>}
      {state === "IDEA_ACCEPTED" && <div className="experiment-success" role="status"><strong>Experiment ready</strong>{acceptedBrief && <><h3>{acceptedBrief.title}</h3><p>{acceptedBrief.core_intent}</p></>}{adviceSource === "RECORDED_FAKE" && <p>Recorded demo advice</p>}<p>The accepted idea is saved as the current version.</p><a href={`/experiments/${encodeURIComponent(id)}`}>View experiment <span aria-hidden="true">↗</span></a></div>}
    </section>}
  </div>;
}
