"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import type { components } from "@/lib/api/schema";

type Profile = components["schemas"]["SetupIdeaProfileRequest"]["profile"];
type SavedProfile = components["schemas"]["SavedIdeaProfileResult"];
const lines = (value: FormDataEntryValue | null) => String(value ?? "").split("\n").map((line) => line.trim()).filter(Boolean);

export function IdeaSetupPanel() {
  const [saved, setSaved] = useState<SavedProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/operator/idea-profile", { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { window.location.replace("/login"); return; }
        if (!response.ok) throw new Error();
        const value: SavedProfile = await response.json();
        if (!("profile" in value)) throw new Error();
        setSaved(value);
        setError("");
      } catch {
        if (!controller.signal.aborted) setError("Could not load your profile. Retry before editing.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [retry]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !saved) return;
    const data = new FormData(event.currentTarget);
    const value = (name: string) => String(data.get(name) ?? "");
    const rate = (name: string) => String(Number((Number(value(name)) / 100).toFixed(6)));
    const profile: Profile = {
      capabilities: lines(data.get("capabilities")), constraints: lines(data.get("constraints")),
      delivery: { max_project_hours: value("max_project_hours"), hours_per_week: value("hours_per_week"), concurrent_projects: Number(value("concurrent_projects")) },
      commercial: { currency: value("currency").toUpperCase(), hourly_cost: value("hourly_cost"), minimum_project_price: value("minimum_project_price"),
        minimum_margin_rate: rate("minimum_margin_rate"), maximum_discount_rate: rate("maximum_discount_rate"), minimum_deposit_rate: rate("minimum_deposit_rate") },
    };
    if (!profile.capabilities.length) { setError("Enter at least one capability."); return; }
    setSaving(true); setError(""); setConfirmation("");
    try {
      const response = await fetch("/api/operator/idea-profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile }), cache: "no-store" });
      if (response.status === 401) { window.location.replace("/login"); return; }
      if (!response.ok) {
        if (response.status === 422) throw new Error("Review your profile values. The server rejected this profile.");
        throw new Error("Could not confirm the save. Your entries are kept; retry saving.");
      }
      const result = await response.json();
      setSaved({ ...result, profile });
      setConfirmation(`Profile saved · version ${result.profile_version}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not confirm the save. Retry saving.");
    } finally { setSaving(false); }
  }

  const profile = saved?.profile;
  function numeric(name: string, label: string, value: number | string | undefined, min: number, max?: number, step = "0.01") {
    return <label className="experiment-field">{label}<input name={name} type="number" required min={min} max={max} step={step} defaultValue={value ?? ""} /></label>;
  }
  return <section className="experiment-workspace profile-workspace">
    <header className="experiment-heading"><div><span className="eyebrow">WORKSPACE SETUP</span><h1>Operator profile</h1><p>Your capabilities and limits guide the agent. Save them once and reuse them across experiments.</p></div></header>
    {loading ? <p role="status">Loading your profile…</p> : <>
      {error && <p className="experiment-error" role="alert">{error}</p>}
      {!saved ? <button type="button" onClick={() => { setLoading(true); setRetry((count) => count + 1); }}>Retry loading</button> : <>
        <p>{saved.profile_version ? `Saved profile · version ${saved.profile_version}` : "No profile saved yet."}</p>
        <form className="profile-form" key={saved.profile_version ?? "new"} onSubmit={(event) => void save(event)}>
          <fieldset disabled={saving}>
            <legend>What you can offer</legend>
            <label className="experiment-field">Capabilities<textarea name="capabilities" required maxLength={100000} defaultValue={profile?.capabilities.join("\n") ?? ""} placeholder="One per line, for example: Python development" /></label>
            <label className="experiment-field">Constraints<textarea name="constraints" maxLength={100000} defaultValue={profile?.constraints.join("\n") ?? ""} placeholder="One per line, for example: No on-site delivery" /></label>
          </fieldset>
          <fieldset disabled={saving}><legend>Delivery capacity</legend><div className="profile-grid">
            {numeric("max_project_hours", "Maximum hours per project", profile?.delivery.max_project_hours, 0.01, 100000)}
            {numeric("hours_per_week", "Hours per week", profile?.delivery.hours_per_week, 0.01, 168)}
            {numeric("concurrent_projects", "Concurrent projects", profile?.delivery.concurrent_projects, 1, 100, "1")}
          </div></fieldset>
          <fieldset disabled={saving}><legend>Commercial limits</legend><p>These are your internal limits, not a price quote or a commitment to a customer.</p><div className="profile-grid">
            <label className="experiment-field">Currency<input name="currency" required pattern="[A-Za-z]{3}" maxLength={3} defaultValue={profile?.commercial.currency ?? ""} placeholder="e.g. ILS" /></label>
            {numeric("hourly_cost", "Your hourly cost", profile?.commercial.hourly_cost, 0, undefined, "0.000001")}
            {numeric("minimum_project_price", "Minimum project price", profile?.commercial.minimum_project_price, 0, undefined, "0.000001")}
            {numeric("minimum_margin_rate", "Minimum margin (%)", profile ? Number((Number(profile.commercial.minimum_margin_rate) * 100).toFixed(4)) : undefined, 0, 100, "0.0001")}
            {numeric("maximum_discount_rate", "Maximum discount (%)", profile ? Number((Number(profile.commercial.maximum_discount_rate) * 100).toFixed(4)) : undefined, 0, 100, "0.0001")}
            {numeric("minimum_deposit_rate", "Minimum deposit (%)", profile ? Number((Number(profile.commercial.minimum_deposit_rate) * 100).toFixed(4)) : undefined, 0, 100, "0.0001")}
          </div></fieldset>
          <p>Research budget per experiment: {saved.budget_usd ? `$${saved.budget_usd}` : "Not configured"}. Set by the workspace policy.</p>
          {confirmation && <p role="status">{confirmation}</p>}
          <div className="experiment-action-row"><button type="submit" disabled={saving}>{saving ? "Saving…" : "Save profile"}</button>{saved.profile_version && <Link href="/experiments/new">Start an experiment</Link>}</div>
        </form>
      </>}
    </>}
  </section>;
}
