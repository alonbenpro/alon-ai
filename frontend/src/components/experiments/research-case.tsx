"use client";

import { useCallback, useEffect, useState } from "react";

export type ResearchCase = {
  experiment_id: string;
  progress: "NOT_STARTED" | "PARTIAL";
  finding_count: number;
  limitations: string[];
  subjects: {
    subject: { artifact_id: string; kind: string; version: number; role: string };
    mode: "CANDIDATE" | "SELECTED" | "SUPPLIED" | "REFINED";
    current: boolean;
    findings: {
      artifact: { artifact_id: string; version: number };
      observation: { run_id?: string; dimension: string; claim: string; finding: string; evidence_status: string; limitations: string[]; step_key: string };
      sources: { reference: { kind: string; retained_id?: string | null; evidence_id?: string | null };
        availability: "CURRENT_SOURCE" | "REFERENCE_ONLY"; provider?: string | null;
        url?: string | null; title?: string | null; available_until?: string | null }[];
    }[];
    coverage: { dimension: string; status: string; finding_ids: string[] }[];
    gaps: string[];
  }[];
};

const label = (value: string) => value.replaceAll("_", " ").toLowerCase();

function currentFirecrawlUrl(source: ResearchCase["subjects"][number]["findings"][number]["sources"][number]): URL | null {
  if (source.availability !== "CURRENT_SOURCE" || source.provider !== "FIRECRAWL" ||
    source.reference.kind !== "RETAINED_CONTENT" || !source.url || !source.available_until ||
    !(Date.parse(source.available_until) > Date.now())) return null;
  try {
    const url = new URL(source.url);
    if (url.protocol !== "https:" || url.username || url.password || !url.hostname ||
      url.hostname === "localhost" || url.hostname.endsWith(".local") ||
      /^\d+(?:\.\d+){3}$/.test(url.hostname) || url.hostname.includes(":")) return null;
    return url;
  } catch { return null; }
}

export function ResearchCasePanel({ experimentId, refreshKey, onCase }: {
  experimentId: string;
  refreshKey?: string;
  onCase?: (value: ResearchCase | null) => void;
}) {
  const [researchCase, setResearchCase] = useState<ResearchCase | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const load = useCallback(async (active: () => boolean) => {
    try {
      const response = await fetch(`/api/operator/experiments/${encodeURIComponent(experimentId)}/research-case`, { cache: "no-store" });
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) throw new Error("CASE_UNAVAILABLE");
      const value = await response.json() as ResearchCase;
      if (!Array.isArray(value.subjects) || !Array.isArray(value.limitations) ||
        typeof value.finding_count !== "number" || value.experiment_id !== experimentId) {
        throw new Error("CASE_INVALID");
      }
      if (!active()) return;
      setResearchCase(value); setUnavailable(false); onCase?.(value);
    } catch {
      if (!active()) return;
      setResearchCase(null); setUnavailable(true); onCase?.(null);
    }
  }, [experimentId, onCase]);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => { if (active) void load(() => active); });
    return () => { active = false; };
  }, [load, refreshKey]);

  const caseBody = researchCase && <>
    <p>{researchCase.progress === "PARTIAL" ? `Partial research record · ${researchCase.finding_count} saved findings. This record does not establish a completed assessment.` : "No completed assessment is available yet."}</p>
    {researchCase.limitations.length > 0 && <div><h3>Case limitations</h3><ul>{researchCase.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
    {researchCase.subjects.map((subject) => <article key={subject.subject.artifact_id} className="experiment-research-subject">
      <h3>{label(subject.mode)} · {subject.current ? "current" : "earlier"} subject</h3>
      <p>Artifact {subject.subject.artifact_id} · v{subject.subject.version}</p>
      <div className="experiment-research-case__columns"><div><h4>Coverage and gaps</h4>
        <ul>{subject.coverage.map((item) => <li key={item.dimension}><strong>{label(item.dimension)}:</strong> {label(item.status)}</li>)}</ul>
        {subject.gaps.length > 0 && <p>Open gaps: {subject.gaps.map(label).join(" · ")}</p>}
      </div><div><h4>Research observations</h4>
        {subject.findings.length === 0 && <p>No research observation has been retained for this subject.</p>}
        {subject.findings.map((finding) => <article key={finding.artifact.artifact_id} className="experiment-research-finding">
          <strong>{label(finding.observation.dimension)} · {label(finding.observation.evidence_status)}</strong>
          <p>{finding.observation.finding}</p><p>Claim assessed: {finding.observation.claim}</p>
          {finding.observation.limitations.length > 0 && <p>Limits: {finding.observation.limitations.join(" · ")}</p>}
          <small>Step {finding.observation.step_key} · Finding {finding.artifact.artifact_id} · v{finding.artifact.version}</small>
          <details><summary>Source references ({finding.sources.length})</summary>{finding.sources.length ? <ul>{finding.sources.map((source, index) => {
            const url = currentFirecrawlUrl(source);
            return <li key={index}>{url ? <a href={url.href} target="_blank" rel="noopener noreferrer">{source.title?.trim() || url.hostname}</a> : "Original source unavailable"}
              {" · "}{source.reference.retained_id ?? source.reference.evidence_id ?? "Reference ID unavailable"}</li>;
          })}</ul> : <p>Agent analysis without a retained source; treat this as unverified.</p>}</details>
        </article>)}
      </div></div>
    </article>)}
  </>;

  return <section className="experiment-research-case" aria-labelledby="research-case-heading">
    <div className="experiment-section-heading"><span>Retained evidence</span><h2 id="research-case-heading">Research details</h2></div>
    {unavailable && <p role="status">Research case is unavailable. The saved run and proposal remain visible; evidence coverage cannot be confirmed here.</p>}
    {!unavailable && !researchCase && <p role="status">Loading retained research…</p>}
    {researchCase && (researchCase.finding_count === 0 ? <details className="experiment-research-case__empty"><summary>Research has not started · 0 saved findings</summary>{caseBody}</details> : caseBody)}
    <button type="button" className="experiment-secondary-action" onClick={() => void load(() => true)}>Refresh research case</button>
  </section>;
}
