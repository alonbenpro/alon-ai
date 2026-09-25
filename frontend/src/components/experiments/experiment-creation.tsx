"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

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
  material_pivot: boolean; grounding_refs: string[]; uncertainties: string[];
};
export type RuntimeReadiness = { provider_mode: "disabled" | "fake" | "live"; ready: boolean };
type Phase = "editing" | "creating" | "refining" | "recovering" | "waiting" | "review" | "accepting" | "accepted" | "error";
type Snapshot = {
  experiment_id: string; name: string; idea_seed: string;
  state: "AWAITING_REFINEMENT" | "REFINEMENT_IN_PROGRESS" | "AWAITING_REVIEW" | "REFINEMENT_FAILED" | "IDEA_ACCEPTED";
  brief: { objective: string; target_customer: string; problem: string; geographies: string[];
    commercial_boundaries: string; budget_usd: string; evidence_definitions: string[] };
  latest_run_id: string | null; advice: Advice | null;
  advice_source: "RECORDED_FAKE" | "OPENAI" | null;
  accepted_brief: Pick<Advice, "title" | "customer" | "problem" | "core_intent" | "material_pivot"> | null;
};

const empty: Values = {
  name: "", ideaSeed: "", objective: "", targetCustomer: "", problem: "",
  geographies: "", commercialBoundaries: "", budgetUsd: "", evidenceDefinitions: "",
  capabilities: "", constraints: "", maxProjectHours: "", hoursPerWeek: "",
  concurrentProjects: "", currency: "", hourlyCost: "", minimumProjectPrice: "",
  minimumMarginRate: "", maximumDiscountRate: "", minimumDepositRate: "",
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
const money = ["budgetUsd", "maxProjectHours", "hoursPerWeek", "concurrentProjects", "hourlyCost", "minimumProjectPrice"] as const;
const rates = ["minimumMarginRate", "maximumDiscountRate", "minimumDepositRate"] as const;
const split = (value: string) => value.split(/\n|,/).map((part) => part.trim()).filter(Boolean);

function complete(values: Values) {
  return Object.values(values).every((value) => value.trim()) &&
    ["geographies", "evidenceDefinitions", "capabilities", "constraints"].every((key) => split(values[key as keyof Values]).length > 0) &&
    money.every((key) => Number.isFinite(Number(values[key])) && Number(values[key]) > 0) &&
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
  if (code.includes("MATERIAL_PIVOT")) return "This advice changes the original direction and cannot be accepted here.";
  if (code === "REFINEMENT_UNAVAILABLE") return "Refinement is unavailable until the governed AI runtime is configured. Your experiment is saved.";
  if (code === "IDEA_VALIDATION_FAILED") return "The refined idea failed validation. Review the original direction and retry refinement.";
  if (code === "EXPERIMENT_NOT_READY" || code === "REFINEMENT_NOT_SUCCESSFUL") return "The experiment is not ready for this step. Refresh the saved experiment and try again.";
  if (code === "IDEA_ALREADY_ACCEPTED") return "This idea has already been accepted. Refresh the saved experiment.";
  if (code === "SESSION_EXPIRED") return "Your session expired. Sign in again to continue.";
  if (code === "VALIDATION_ERROR") return "Review the experiment bounds and try again.";
  return `${action} could not finish. Your entered information is still here; try again.`;
}

export function ExperimentCreation({ experimentId, runtime }: { experimentId?: string; runtime: RuntimeReadiness | null }) {
  const [values, setValues] = useState<Values>(empty);
  const [phase, setPhase] = useState<Phase>(experimentId ? "recovering" : "editing");
  const [id, setId] = useState(experimentId ?? "");
  const [runId, setRunId] = useState("");
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [acceptedBrief, setAcceptedBrief] = useState<Snapshot["accepted_brief"]>(null);
  const [adviceSource, setAdviceSource] = useState<Snapshot["advice_source"]>(null);
  const [message, setMessage] = useState("");
  const [retryAllowed, setRetryAllowed] = useState(false);
  const [liveConfirmed, setLiveConfirmed] = useState(false);
  const createKey = useRef("");
  const refineKey = useRef("");
  const acceptKey = useRef("");

  useEffect(() => {
    if (!experimentId) return;
    let active = true;
    let seenRunning = false;
    let timer: number | undefined;
    const load = async () => {
      try {
        const response = await fetch(`/api/operator/experiments/${encodeURIComponent(experimentId)}`, { cache: "no-store" });
        if (response.status === 401) { window.location.replace("/login"); return; }
        if (!response.ok) throw new Error("unavailable");
        const saved = await response.json() as Snapshot;
        if (!active) return;
        setId(saved.experiment_id);
        setValues({ ...empty, name: saved.name, ideaSeed: saved.idea_seed,
          objective: saved.brief.objective, targetCustomer: saved.brief.target_customer,
          problem: saved.brief.problem, geographies: saved.brief.geographies.join("\n"),
          commercialBoundaries: saved.brief.commercial_boundaries, budgetUsd: saved.brief.budget_usd,
          evidenceDefinitions: saved.brief.evidence_definitions.join("\n") });
        setRunId(saved.latest_run_id ?? "");
        setAdvice(saved.advice);
        setAcceptedBrief(saved.accepted_brief);
        setAdviceSource(saved.advice_source);
        setMessage("");
        setRetryAllowed(false);
        if (saved.state === "IDEA_ACCEPTED") setPhase("accepted");
        else if (saved.state === "AWAITING_REVIEW" && saved.advice && saved.latest_run_id) setPhase("review");
        else if (saved.state === "REFINEMENT_IN_PROGRESS") {
          seenRunning = true;
          setPhase("waiting");
          timer = window.setTimeout(() => void load(), 3000);
        }
        else {
          setPhase("error");
          setRetryAllowed(saved.state === "REFINEMENT_FAILED" || saved.state === "AWAITING_REFINEMENT");
          setMessage(saved.state === "REFINEMENT_FAILED" ? "Refinement could not finish. Retry the saved experiment." : "Your experiment is saved and ready for refinement.");
        }
      } catch {
        if (!active) return;
        if (seenRunning) {
          setPhase("waiting");
          setMessage("Refinement status temporarily unavailable. Checking again; no new run will start.");
          timer = window.setTimeout(() => void load(), 3000);
        } else {
          setPhase("error");
          setRetryAllowed(false);
          setMessage("Experiment could not be loaded. Refresh to check its status.");
        }
      }
    };
    void load();
    return () => { active = false; if (timer !== undefined) window.clearTimeout(timer); };
  }, [experimentId]);

  const change = (key: keyof Values, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
    createKey.current = "";
    if (phase === "editing") setMessage("");
  };
  const refine = async (experiment: string) => {
    if (!runtime?.ready) { setMessage("Refinement is unavailable. Refresh after the runtime is configured."); return; }
    if (runtime.provider_mode === "live" && !liveConfirmed) { setMessage("Confirm the live call before starting refinement."); return; }
    setPhase("refining"); setMessage("");
    try {
      refineKey.current ||= crypto.randomUUID();
      const result = await post(`/api/operator/experiments/${encodeURIComponent(experiment)}/refine`,
        { idempotency_key: refineKey.current });
      if (result.state !== "AWAITING_REVIEW" || !result.run_id || !result.advice) throw new Error("REFINEMENT_FAILED");
      setRunId(result.run_id); setAdvice(result.advice);
      setAdviceSource(result.advice_source ?? null); setPhase("review");
    } catch (error) {
      setPhase("error"); setRetryAllowed(true); setMessage(failure(error, "Refinement"));
    }
  };
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!complete(values)) { setMessage("Complete the experiment bounds with valid amounts and rates before continuing."); return; }
    if (!runtime?.ready) { setMessage("Refinement is unavailable. Refresh after the runtime is configured."); return; }
    if (runtime.provider_mode === "live" && !liveConfirmed) { setMessage("Confirm the live call before creating and refining."); return; }
    setPhase("creating"); setMessage("");
    try {
      createKey.current ||= crypto.randomUUID();
      const result = await post("/api/operator/experiments", {
        name: values.name.trim(), idea_seed: values.ideaSeed,
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
        command_key: createKey.current,
      });
      if (result.state !== "AWAITING_REFINEMENT" || typeof result.experiment_id !== "string") throw new Error("CREATE_UNCONFIRMED");
      setId(result.experiment_id);
      window.history.replaceState(null, "", `/experiments/${encodeURIComponent(result.experiment_id)}`);
      await refine(result.experiment_id);
    } catch (error) {
      setPhase("error"); setMessage(failure(error, "Creation"));
    }
  };
  const accept = async () => {
    if (!id || !runId || !advice || advice.material_pivot) return;
    setPhase("accepting"); setMessage("");
    try {
      acceptKey.current ||= crypto.randomUUID();
      const result = await post(`/api/operator/experiments/${encodeURIComponent(id)}/accept`,
        { run_id: runId, command_key: acceptKey.current });
      if (result.state !== "IDEA_ACCEPTED" || result.experiment_id !== id || !result.idea_brief_artifact_id) throw new Error("ACCEPT_UNCONFIRMED");
      setAcceptedBrief(advice);
      setPhase("accepted");
    } catch (error) {
      setPhase("review"); setMessage(failure(error, "Acceptance"));
    }
  };

  return <div className="experiment-workspace">
    <div className="experiment-heading"><p className="eyebrow">Experiment / idea origin</p><h1>Start with a direction.<br /><em>Make it testable.</em></h1><p>Set the boundaries, preserve your original idea, then review the refined direction before saving it.</p></div>
    <div className="experiment-step-track" aria-label="Creation stages"><span className={phase === "editing" || phase === "creating" ? "current" : "done"}>01 · Define</span><span className={phase === "refining" || phase === "waiting" ? "current" : phase === "review" || phase === "accepting" || phase === "accepted" ? "done" : ""}>02 · Refine</span><span className={phase === "review" || phase === "accepting" ? "current" : phase === "accepted" ? "done" : ""}>03 · Review</span></div>
    {phase !== "accepted" && <div className={runtime?.provider_mode === "live" && runtime.ready ? "experiment-runtime experiment-runtime--live" : "experiment-runtime"} role="note">
      {runtime?.ready && runtime.provider_mode === "live" ? <><strong>Live OpenAI refinement</strong><p>Creating this experiment will start a live model call. It may incur a cost under the research budget you enter. Review the preview before continuing.</p><label><input type="checkbox" checked={liveConfirmed} onChange={(event) => setLiveConfirmed(event.target.checked)} /> I understand this may incur a cost</label></> :
        runtime?.ready && runtime.provider_mode === "fake" ? <><strong>Recorded demo mode</strong><p>Refinement uses synthetic recorded advice. No live OpenAI call is made.</p></> :
          <><strong>Refinement is unavailable</strong><p>The server has not confirmed an available runtime. Refresh after it is configured.</p></>}
    </div>}
    <div className="experiment-columns"><section className="experiment-form-panel" aria-labelledby="setup-heading">
      <div className="experiment-section-heading"><span>01 / Setup</span><h2 id="setup-heading">Your starting point</h2></div>
      {id ? <div className="experiment-saved-seed"><span className="eyebrow">Original idea · saved exactly</span><pre>{values.ideaSeed}</pre><p>Experiment ID: {id}</p></div> :
        <form onSubmit={(event) => void create(event)} noValidate><div className="experiment-fields">
          {fields.map(({ key, label, hint, tall }) => <label className={tall ? "experiment-field experiment-field--wide" : "experiment-field"} key={key}><span>{label}</span>
            {tall ? <textarea aria-label={label} name={key} value={values[key]} onChange={(event) => change(key, event.target.value)} rows={key === "ideaSeed" ? 4 : 2} /> :
              <input aria-label={label} name={key} type="text" inputMode={money.includes(key as typeof money[number]) || rates.includes(key as typeof rates[number]) ? "decimal" : "text"} value={values[key]} onChange={(event) => change(key, event.target.value)} />}
            {hint && <small>{hint}</small>}</label>)}
          <label className="experiment-field"><span>Currency</span><select name="currency" value={values.currency} onChange={(event) => change("currency", event.target.value)}><option value="">Select currency</option><option value="ILS">ILS</option><option value="USD">USD</option></select></label>
        </div>{message && <p className="experiment-error" role="alert">{message}</p>}<div className="experiment-action-row"><button type="submit" disabled={!runtime?.ready || phase === "creating" || phase === "refining"}>Create and refine <span aria-hidden="true">↗</span></button><span>First stage: SHADOW</span></div></form>}
    </section><aside className="experiment-preview" aria-label="Experiment preview"><div className="experiment-section-heading"><span>Live preview</span><h2>Mission brief</h2></div>
      <dl><div><dt>Customer</dt><dd>{values.targetCustomer || "Awaiting target"}</dd></div><div><dt>Problem</dt><dd>{values.problem || "Awaiting hypothesis"}</dd></div><div><dt>Geography</dt><dd>{values.geographies || "Awaiting location"}</dd></div><div><dt>Research budget</dt><dd>{values.budgetUsd ? `$${values.budgetUsd}` : "Awaiting budget"}</dd></div><div><dt>First stage</dt><dd>SHADOW</dd></div></dl>
      <div className="experiment-seed-preview"><span className="eyebrow">Original text</span><pre data-testid="seed-preview">{values.ideaSeed}</pre></div><p className="experiment-preview-note">A refined idea becomes current only after you accept the server’s advice.</p>
    </aside></div>
    {id && <section className="experiment-review" aria-live="polite" aria-labelledby="refinement-heading"><div className="experiment-section-heading"><span>02 / Refinement</span><h2 id="refinement-heading">Idea review</h2></div>
      {(phase === "refining" || phase === "recovering") && <p role="status">{phase === "recovering" ? "Loading saved experiment…" : "Refining your idea…"}</p>}
      {phase === "waiting" && <div role="status"><p>Refinement in progress. This page checks for server confirmation automatically.</p>{message && <p>{message}</p>}</div>}
      {phase === "error" && <div><p className="experiment-error" role="alert">{message}</p>{retryAllowed ? <button type="button" disabled={!runtime?.ready} onClick={() => void refine(id)}>Retry refinement</button> : <a href={`/experiments/${encodeURIComponent(id)}`}>Reload status</a>}</div>}
      {advice && (phase === "review" || phase === "accepting") && <div className="experiment-advice"><div className="experiment-advice__lead"><span className="eyebrow">{adviceSource === "RECORDED_FAKE" ? "Recorded demo advice" : "Proposed direction · unaccepted advice"}</span><h3>{advice.title}</h3><p>{advice.core_intent}</p></div><dl><div><dt>Customer</dt><dd>{advice.customer}</dd></div><div><dt>Problem</dt><dd>{advice.problem}</dd></div><div><dt>Grounded in</dt><dd>{advice.grounding_refs.join(" · ")}</dd></div></dl><div className="experiment-uncertainties"><h4>Starting assumptions <small>supplied by you</small></h4><ul aria-label="Starting assumptions"><li>Customer: <span>{values.targetCustomer}</span></li><li>Problem: <span>{values.problem}</span></li><li>Objective: <span>{values.objective}</span></li></ul><h4>Unknowns to test <small>from refinement advice</small></h4><ul aria-label="Unknowns to test">{advice.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul></div>
        {advice.material_pivot ? <p className="experiment-error" role="alert">This proposal changes the original direction. It needs a separate operator decision and cannot be accepted here.</p> : <button type="button" disabled={phase === "accepting"} onClick={() => void accept()}>Accept and save idea</button>}
        {message && phase === "review" && <p className="experiment-error" role="alert">{message}</p>}</div>}
      {phase === "accepted" && <div className="experiment-success" role="status"><strong>Experiment ready</strong>{acceptedBrief && <><h3>{acceptedBrief.title}</h3><p>{acceptedBrief.core_intent}</p></>}{adviceSource === "RECORDED_FAKE" && <p>Recorded demo advice</p>}<p>The refined idea is saved as the current accepted version.</p><a href={`/experiments/${encodeURIComponent(id)}`}>View experiment <span aria-hidden="true">↗</span></a></div>}
    </section>}
  </div>;
}
