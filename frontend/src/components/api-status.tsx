"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReadiness } from "@/lib/api/readiness";

function StatusDot({ tone }: { tone: "online" | "unavailable" | "disabled" }) {
  return <span aria-hidden="true" className={`status-dot status-dot--${tone}`} />;
}

function RouteLine({ state }: { state: "pending" | "success" | "failure" }) {
  return (
    <svg
      aria-hidden="true"
      className={`readiness-route readiness-route--${state}`}
      focusable="false"
      preserveAspectRatio="none"
      viewBox="0 0 500 600"
    >
      <path
        className="route-solid"
        d="M0 1 H18 Q42 1 42 27 V154 Q42 176 64 176 H76 Q92 176 92 192 V355 M42 1 H500"
      />
      <path className="route-dashed" d="M92 355 V505" />
    </svg>
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

        <p className="status-row status-row--outreach">
          <StatusDot tone="disabled" />
          <span>Outreach disabled by default</span>
        </p>
      </div>
    </section>
  );
}
