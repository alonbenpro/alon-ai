"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReadiness } from "@/lib/api/readiness";

function StatusDot({ tone }: { tone: "online" | "unavailable" | "disabled" }) {
  return <span aria-hidden="true" className={`status-dot status-dot--${tone}`} />;
}

function RouteLine({ state }: { state: "pending" | "success" | "failure" }) {
  return (
    <div
      aria-hidden="true"
      className={`readiness-route readiness-route--${state}`}
    >
      <span className="route-entry" />
      <span className="route-top-tail" />
      <span className="route-primary-leg" />
      <span className="route-step" />
      <span className="route-database-leg" />
      <span className="route-dashed" />
    </div>
  );
}

export function ApiStatus() {
  const query = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 30_000,
  });

  const state = query.isPending
    ? "pending"
    : query.isError
      ? "failure"
      : "success";

  return (
    <section
      aria-labelledby="readiness-title"
      className="readiness"
      data-readiness-state={state}
    >
      <RouteLine state={state} />
      <h2 id="readiness-title">System readiness</h2>

      <div className="readiness-states">
        <div aria-atomic="true" aria-live="polite" role="status">
          {query.isPending ? (
            <p className="status-row status-row--primary">
              <StatusDot tone="unavailable" />
              <span>Checking services…</span>
            </p>
          ) : query.isError ? (
            <p className="status-row status-row--primary">
              <StatusDot tone="unavailable" />
              <span>Services unavailable</span>
            </p>
          ) : (
            <dl>
              <div className="status-row status-row--api">
                <dt aria-label="API" className="visually-hidden" />
                <dd>
                  <StatusDot tone="online" />
                  <span>API online</span>
                </dd>
              </div>
              <div className="status-row status-row--database">
                <dt aria-label="Database" className="visually-hidden" />
                <dd>
                  <StatusDot tone="online" />
                  <span>Database online</span>
                </dd>
              </div>
            </dl>
          )}
        </div>

        <p className="status-row status-row--outreach">
          <StatusDot tone="disabled" />
          <span>Outreach disabled by default</span>
        </p>
      </div>
    </section>
  );
}
