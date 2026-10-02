"use client";

import { useCallback, useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";

type RunView = components["schemas"]["RunView"];
type RunEvents = components["schemas"]["RunEvents"];
type RunResult = components["schemas"]["RunResult"];
type TerminalStatus = "SUCCEEDED" | "BLOCKED" | "FAILED" | "CANCELLED" | "OUTCOME_UNKNOWN";
const terminalStatuses = new Set<TerminalStatus>(["SUCCEEDED", "BLOCKED", "FAILED", "CANCELLED", "OUTCOME_UNKNOWN"]);

function isTerminal(status: RunView["status"]): status is TerminalStatus {
  return terminalStatuses.has(status as TerminalStatus);
}

function errorText(value: unknown, fallback: string) {
  if (typeof value === "object" && value !== null && "detail" in value && typeof value.detail === "string") {
    const detail = value.detail;
    if (detail === "LIVE_CONFIG_REQUIRED") return `${detail}: The live provider is not configured or authorized.`;
    return detail;
  }
  return fallback;
}

function groundingReferences(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(groundingReferences);
  if (typeof value !== "object" || value === null) return [];
  return Object.entries(value).flatMap(([key, child]) => key === "grounding_refs" && Array.isArray(child)
    ? child.filter((reference): reference is string => typeof reference === "string")
    : groundingReferences(child));
}

function elapsed(startedAt: string | null | undefined, finishedAt: string | null | undefined) {
  if (!startedAt) return "Not started";
  const start = Date.parse(startedAt);
  const end = finishedAt ? Date.parse(finishedAt) : Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "Unavailable";
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function usd(value: string | null | undefined) {
  return value == null ? "Not recorded" : `$${value}`;
}

function hasUnresolvedReceipt(receipts: RunView["receipts"] | RunResult["receipts"] | undefined) {
  return receipts?.some((receipt) => receipt.state !== "FINAL") ?? false;
}

function costSummary(run: RunView, result: RunResult | null) {
  const actual = run.actual_cost_usd ?? result?.actual_cost_usd;
  if (actual != null) return usd(actual);
  if (run.pending_cost_usd != null || hasUnresolvedReceipt(run.receipts) || hasUnresolvedReceipt(result?.receipts)) {
    return "Awaiting reconciliation";
  }
  return "Not recorded";
}

function savedRejectCommand(runId: string): { command_key: string; reason: string } | null {
  try {
    const stored = sessionStorage.getItem(`agent-run-${runId}-reject-command`);
    if (!stored) return null;
    const pending = JSON.parse(stored) as { command_key?: unknown; reason?: unknown };
    if (typeof pending.command_key === "string" && typeof pending.reason === "string") {
      return { command_key: pending.command_key, reason: pending.reason };
    }
  } catch { /* malformed session data cannot authorize a command */ }
  return null;
}

function statusLabel(run: RunView) {
  const status = String(run.status ?? "UNKNOWN");
  if (status === "BLOCKED") return "Blocked";
  if (run.provider_mode === "fake") return "Recorded example";
  if (run.provider_mode === "disabled") return "Disabled";
  return status === "SUCCEEDED" ? "Live · complete" : status === "RUNNING" ? "Live · running" :
    status === "QUEUED" ? "Live · queued" : `Live · ${status.toLowerCase().replaceAll("_", " ")}`;
}

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase();
}

function stepLabel(kind: string) {
  return kind.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eventSummary(event: RunEvents["events"][number]) {
  return [...new Set([event.diagnostic?.code, event.detail].filter((value): value is string => Boolean(value)))].join(" · ");
}

function firstIdeaInput(inputs: NonNullable<RunView["resolved_inputs"]>) {
  const seed = inputs.find((input) => input.kind === "IDEA_SEED");
  const payload = seed?.payload;
  if (!payload || typeof payload !== "object") return null;
  if ("statement" in payload && typeof payload.statement === "string") {
    return payload.statement;
  }
  if ("idea_seed" in payload && typeof payload.idea_seed === "string") {
    return payload.idea_seed;
  }
  return null;
}

export function RunInspector({ experimentId, runId, legacyPendingReview = false, onRejected, onReviewStatus, onResearchStatus }: {
  experimentId: string;
  runId: string;
  legacyPendingReview?: boolean;
  onRejected?: () => void;
  onReviewStatus?: (runId: string, status: RunView["review_status"]) => void;
  onResearchStatus?: (run: RunView) => void;
}) {
  const [run, setRun] = useState<RunView | null>(null);
  const [legacyMissing, setLegacyMissing] = useState(false);
  const [events, setEvents] = useState<RunEvents["events"]>([]);
  const [result, setResult] = useState<RunResult | null>(null);
  const [message, setMessage] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [pendingReject, setPendingReject] = useState<{ command_key: string; reason: string } | null>(null);
  const [busy, setBusy] = useState("");
  const [, setClock] = useState(0);

  const load = useCallback(async (active: () => boolean) => {
    try {
      const [runRead, eventRead] = await Promise.allSettled([
        fetch(`/api/operator/agent-runs/${encodeURIComponent(runId)}`, { cache: "no-store" }),
        fetch(`/api/operator/agent-runs/${encodeURIComponent(runId)}/events`, { cache: "no-store" }),
      ]);
      if (runRead.status === "rejected") throw runRead.reason;
      const response = runRead.value;
      const eventResponse = eventRead.status === "fulfilled" ? eventRead.value : null;
      if (response.status === 401 || eventResponse?.status === 401) { window.location.replace("/login"); return null; }
      if (response.status === 404 && legacyPendingReview) {
        if (active()) {
          setLegacyMissing(true);
          onReviewStatus?.(runId, "PENDING");
          setMessage("");
        }
        return null;
      }
      if (!response.ok) throw new Error(errorText(await response.json().catch(() => null), "Run status is unavailable."));
      const nextRun = await response.json() as RunView;
      if (active()) {
        setRun(nextRun);
        onReviewStatus?.(nextRun.run_id, nextRun.review_status);
        onResearchStatus?.(nextRun);
      }
      if (eventResponse?.ok) {
        const nextEvents = await eventResponse.json() as RunEvents;
        if (active()) setEvents(Array.isArray(nextEvents.events) ? nextEvents.events : []);
      }
      if (isTerminal(nextRun.status)) {
        try {
          const resultResponse = await fetch(`/api/operator/agent-runs/${encodeURIComponent(runId)}/result`, { cache: "no-store" });
          if (resultResponse.status === 401) { window.location.replace("/login"); return nextRun; }
          if (resultResponse.ok) {
            const nextResult = await resultResponse.json() as RunResult;
            if (active()) setResult(nextResult);
          }
        } catch { /* the run view still carries the retained terminal result */ }
      }
      if (active()) setMessage(eventResponse?.ok ? "" : "Run events are temporarily unavailable.");
      return nextRun;
    } catch (error) {
      if (active()) setMessage(error instanceof Error ? error.message : "Run status is unavailable.");
      return null;
    }
  }, [runId, legacyPendingReview, onReviewStatus, onResearchStatus]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const refresh = async () => {
      const nextRun = await load(() => active);
      if (!active) return;
      if (nextRun && !isTerminal(nextRun.status)) timer = window.setTimeout(() => void refresh(), 2500);
    };
    void refresh();
    return () => { active = false; if (timer !== undefined) window.clearTimeout(timer); };
  }, [load]);

  useEffect(() => {
    if (run?.status !== "QUEUED" && run?.status !== "RUNNING") return;
    const timer = window.setInterval(() => setClock((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [run?.status]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      const pending = savedRejectCommand(runId);
      if (active && pending) {
        setPendingReject(pending);
        setRejectReason(pending.reason);
      }
    });
    return () => { active = false; };
  }, [runId]);

  const cancelCommand = () => {
    const storageKey = `agent-run-${runId}-cancel-command`;
    try {
      const existing = sessionStorage.getItem(storageKey);
      if (existing) return { key: existing, storageKey };
    } catch { /* session storage can be unavailable in restricted browser contexts */ }
    const key = crypto.randomUUID();
    try { sessionStorage.setItem(storageKey, key); } catch { /* continue for this page session */ }
    return { key, storageKey };
  };

  const cancel = async () => {
    if (!run || busy) return;
    const pending = cancelCommand();
    setBusy("cancel"); setMessage("");
    try {
      const response = await fetch(`/api/operator/agent-runs/${encodeURIComponent(runId)}/cancel`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_key: pending.key }), cache: "no-store",
      });
      const body: unknown = await response.json().catch(() => null);
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error(errorText(body, "Cancellation could not be confirmed."));
      if (body && typeof body === "object" && "confirmed" in body && body.confirmed === true) {
        try { sessionStorage.removeItem(pending.storageKey); } catch { /* no-op */ }
      }
      await load(() => true);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Cancellation could not be confirmed."); }
    finally { setBusy(""); }
  };

  const reject = async () => {
    if (!run || busy || !rejectReason.trim()) return;
    const pending = pendingReject ?? { command_key: crypto.randomUUID(), reason: rejectReason.trim() };
    try { sessionStorage.setItem(`agent-run-${runId}-reject-command`, JSON.stringify(pending)); } catch { /* continue for this page session */ }
    setPendingReject(pending);
    setBusy("reject"); setMessage("");
    try {
      const response = await fetch(`/api/operator/agent-runs/${encodeURIComponent(runId)}/reject`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pending), cache: "no-store",
      });
      const body: unknown = await response.json().catch(() => null);
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error(errorText(body, "Run rejection could not be confirmed."));
      setRun(body as RunView); setRejectReason("");
      onReviewStatus?.((body as RunView).run_id, (body as RunView).review_status);
      try { sessionStorage.removeItem(`agent-run-${runId}-reject-command`); } catch { /* no-op */ }
      setPendingReject(null);
      onRejected?.();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Run rejection could not be confirmed."); }
    finally { setBusy(""); }
  };

  if (!runId) return null;
  if (legacyMissing) return <section className="agent-run-inspector" aria-labelledby="run-inspector-heading">
    <div className="experiment-section-heading"><span>Saved suggestion</span><h2 id="run-inspector-heading">Agent run</h2></div>
    <p role="status">Legacy saved suggestion · no run record was retained. Review the saved proposal above before accepting it.</p>
  </section>;
  if (!run) return <section className="agent-run-inspector" aria-labelledby="run-inspector-heading">
    <div className="experiment-section-heading"><span>Saved service run</span><h2 id="run-inspector-heading">Agent run</h2></div>
    {message ? <p className="experiment-error" role="alert">{message}</p> : <p role="status">Loading saved run…</p>}
    <button type="button" onClick={() => void load(() => true)}>Refresh run</button>
  </section>;

  const inputs = run.resolved_inputs?.length ? run.resolved_inputs : run.input_refs ?? [];
  const output = run.output ?? result?.output;
  const diagnostic = run.diagnostic ?? result?.diagnostic ?? null;
  const suppliedIdea = firstIdeaInput(inputs);
  const references = groundingReferences(output);
  const summaryFinding = typeof run.research_summary?.finding === "string" ? run.research_summary.finding : null;
  const summaryLimitations = Array.isArray(run.research_summary?.limitations) ?
    run.research_summary.limitations.filter((value): value is string => typeof value === "string") : [];
  return <section className="agent-run-inspector" aria-labelledby="run-inspector-heading">
    <div className="agent-run-inspector__heading">
      <div className="experiment-section-heading"><span>{String(run.task_kind ?? "agent run").replaceAll("_", " ")}</span><h2 id="run-inspector-heading">Agent activity</h2></div>
      <span role="status" className={`status-pill status-pill--${run.status === "SUCCEEDED" ? "completed" : run.status === "RUNNING" || run.status === "QUEUED" ? "running" : "blocked"}`}>{statusLabel(run)}</span>
    </div>
    <dl className="agent-run-inspector__facts" aria-label="Run summary">
      <div><dt>Elapsed</dt><dd>{elapsed(run.started_at, run.finished_at)}</dd></div>
      <div><dt>Model</dt><dd>{run.model_identifier ?? "Not recorded"}</dd></div>
      <div><dt>Cost</dt><dd>{costSummary(run, result)}</dd></div>
      <div><dt>Research</dt><dd>{label(run.research_status)}</dd></div>
    </dl>
    {message && <p className="experiment-error" role="alert">{message}</p>}
    {diagnostic ? <section className="agent-run-inspector__diagnostic" aria-labelledby="run-error-heading" role="alert">
      <div><span>Needs attention</span><h3 id="run-error-heading">Run error</h3></div>
      <p>{diagnostic.message}</p>
      <dl><div><dt>Stage</dt><dd>{diagnostic.stage}</dd></div><div><dt>Error type</dt><dd>{diagnostic.error_type}</dd></div><div><dt>Code</dt><dd>{diagnostic.code}</dd></div></dl>
      {diagnostic.frames.length > 0 && <details><summary>Diagnostic frames</summary><pre>{diagnostic.frames.join("\n")}</pre></details>}
    </section> : run.blocked_reason && <section className="agent-run-inspector__blocked" aria-labelledby="run-error-heading" role="alert"><h3 id="run-error-heading">Run error</h3><p><strong>{run.blocked_reason}</strong>{run.blocked_reason === "LIVE_CONFIG_REQUIRED" ? " — live provider credentials or authorization are missing." : ""}</p><p>No diagnostic detail was retained for this run.</p></section>}
    {Boolean(summaryFinding || run.research_gaps?.length) && <div className="agent-run-inspector__events"><h3>Research assessment</h3>
      {summaryFinding && <p>{summaryFinding}</p>}
      {summaryLimitations.length ? <p>Limits: {summaryLimitations.join(" · ")}</p> : null}
      {run.research_gaps?.length ? <p>Open gaps: {run.research_gaps.join(" · ")}</p> : null}
    </div>}
    {run.cancel_requested && <p className="agent-run-inspector__cancel" role="status">{run.cancel_confirmed ? "Cancellation confirmed by the service." : "Cancellation requested. The service has not confirmed that the run stopped."}</p>}
    <div className="agent-run-inspector__grid">
      <section><h3>Agent request</h3>
        {suppliedIdea ? <p className="agent-run-inspector__idea">{suppliedIdea}</p> : <p>No saved idea input was returned.</p>}
        <details><summary>View retained request context</summary>
          {inputs.length ? inputs.map((input) => <article key={input.artifact_id} className="agent-run-inspector__record"><small>{input.kind} · v{input.version} · {input.role}</small><pre>{JSON.stringify(input.payload, null, 2)}</pre></article>) : null}
          {run.operator_profile && <article className="agent-run-inspector__record"><small>Operator profile · v{run.operator_profile.version}</small><pre>{JSON.stringify(run.operator_profile, null, 2)}</pre></article>}
        </details>
      </section>
      <section><h3>Agent response</h3>{output ? <>
        {typeof output.title === "string" && <strong>{output.title}</strong>}
        {(typeof output.core_intent === "string" || typeof output.customer === "string" || typeof output.problem === "string") && <dl className="agent-run-inspector__response">
          {typeof output.core_intent === "string" && <div><dt>Idea</dt><dd>{output.core_intent}</dd></div>}
          {typeof output.customer === "string" && <div><dt>For</dt><dd>{output.customer}</dd></div>}
          {typeof output.problem === "string" && <div><dt>Problem</dt><dd>{output.problem}</dd></div>}
        </dl>}
        <details><summary>View saved response</summary><pre>{JSON.stringify(output, null, 2)}</pre></details>
        {references.length > 0 && <p>Source references: {references.join(" · ")}</p>}
      </> : <p>{isTerminal(run.status) ? "No response was recorded for this run." : "The response will appear when the agent finishes."}</p>}</section>
    </div>
    <details className="agent-run-inspector__usage">
      <summary>Cost details</summary>
      {run.provider_mode === "fake" && <p>Recorded ledger amounts are synthetic; no provider charge occurred.</p>}
      <dl><div><dt>{run.provider_mode === "fake" ? "Recorded reservation" : "Pending cost"}</dt><dd>{usd(run.pending_cost_usd)}</dd></div><div><dt>{run.provider_mode === "fake" ? "Recorded ledger cost" : "Actual cost"}</dt><dd>{run.provider_mode === "fake" ? usd(run.actual_cost_usd ?? result?.actual_cost_usd) : costSummary(run, result)}</dd></div></dl>
      {run.usage?.length ? <ul>{run.usage.map((item, index) => <li key={`${item.component}-${index}`}>
        {item.component}: {item.quantity ?? "Quantity unavailable"} · {item.cost == null ? "Cost unavailable" : `${item.currency} ${item.cost}`} · {item.knowledge.toLowerCase()}
      </li>)}</ul> : <p>No usage record has been retained.</p>}
    </details>
    <div className="agent-run-inspector__events"><h3>Activity timeline</h3>{events.length ? <ol>{events.map((event) => <li key={event.sequence}>
      <time dateTime={event.at}>{event.at}</time><strong>{event.type.replaceAll("_", " ")}</strong>{eventSummary(event) && <span>{eventSummary(event)}</span>}
    </li>)}</ol> : <p>No events have been recorded.</p>}</div>
    {run.steps && <details className="agent-run-inspector__events"><summary>Provider call details</summary>{run.steps.length ? <ol>{run.steps.map((step) => <li key={step.step_key}>
      <span>{step.ordinal}. {stepLabel(step.kind)}</span><strong>{step.status.replaceAll("_", " ")}</strong>
      <span>{step.reason_code ?? ""}{step.result_artifact_id ? ` · Result ${step.result_artifact_id}` : ""}
        {step.provider_call_id ? ` · Call ${step.provider_call_id}` : ""}</span>
    </li>)}</ol> : <p>No child steps have been retained.</p>}</details>}
    {(run.status === "QUEUED" || run.status === "RUNNING") && <button type="button" className="experiment-secondary-action" disabled={!!busy || run.cancel_confirmed} onClick={() => void cancel()}>
      {run.cancel_confirmed ? "Run cancelled" : busy === "cancel" ? "Requesting cancellation…" : run.cancel_requested ? "Retry cancellation" : "Cancel run"}
    </button>}
    {run.status === "SUCCEEDED" && run.review_status === "PENDING" && <div className="agent-run-inspector__reject">
      <label className="experiment-field"><span>Reject this result <small>Explain the issue</small></span><textarea aria-label="Reason for rejecting run" value={rejectReason} disabled={!!pendingReject || !!busy} onChange={(event) => setRejectReason(event.target.value)} rows={2} /></label>
      <button type="button" className="experiment-secondary-action" disabled={!rejectReason.trim() || !!busy} onClick={() => void reject()}>
        {busy === "reject" ? "Saving rejection…" : "Reject run"}
      </button>
    </div>}
    {run.review_status === "REJECTED" && <p role="status">This run was rejected. Its output remains available for review.</p>}
    {run.review_status === "ACCEPTED" && <p role="status">This run was accepted.</p>}
    <details className="agent-run-inspector__technical"><summary>Technical details</summary>
      <dl><div><dt>Run ID</dt><dd>{run.run_id}</dd></div><div><dt>Profile</dt><dd>{run.profile_id} · v{run.profile_version}</dd></div><div><dt>Output source</dt><dd>{run.advice_source ?? "Not recorded"}</dd></div><div><dt>Review</dt><dd>{run.review_status}</dd></div><div><dt>Receipt</dt><dd>{run.receipt_id ?? result?.receipt_id ?? "Not recorded"}</dd></div></dl>
      {run.receipts?.length ? <details><summary>Provider receipts ({run.receipts.length})</summary><ul>{run.receipts.map((receipt) => <li key={receipt.receipt_id}>{receipt.provider} · {receipt.state} · {receipt.receipt_id} · reserved {receipt.currency} {receipt.reserved} · accrued {receipt.currency} {receipt.accrued}</li>)}</ul></details> : <p>No provider receipt was retained.</p>}
    </details>
    <button type="button" className="agent-run-inspector__refresh" disabled={!!busy} onClick={() => void load(() => true)}>Refresh run</button>
    <span className="visually-hidden">Experiment {experimentId}</span>
  </section>;
}
