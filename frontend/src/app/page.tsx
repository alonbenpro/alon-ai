import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";

import { ActivityFeed } from "@/components/operator/activity-feed";
import { OperatorControls } from "@/components/operator/operator-controls";
import { StatusOverview } from "@/components/operator/status-overview";
import { backendFetch, getSession } from "@/lib/operator/server";
import { parseActivity, parseStatus } from "@/lib/operator/types";

export const dynamic = "force-dynamic";

async function loadProjection(path: string): Promise<unknown> {
  try {
    const response = await backendFetch(path);
    return response.ok ? await response.json() : null;
  } catch { return null; }
}

export default async function Home() {
  const session = await getSession();
  if (session.kind === "unauthenticated") redirect("/login");
  if (session.kind === "unavailable") {
    return <main className="access-unavailable"><div className="access-unavailable__panel"><span className="eyebrow">Access check unavailable</span><h1>We can’t verify this session.</h1><p>The operator service did not confirm access. Retry when the connection is restored.</p><Link href="/">Retry access check</Link></div></main>;
  }

  const [statusData, activityData] = await Promise.all([
    loadProjection("/operator/status"),
    loadProjection("/operator/activity"),
  ]);
  const status = parseStatus(statusData);
  const activity = parseActivity(activityData);

  return (
    <div className="operator-app" id="overview">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="operator-sidebar" aria-label="Primary navigation">
        <a className="operator-brand" href="#overview" aria-label="Alon AI overview"><Image src="/alon-ai-mark.png" alt="" width={42} height={42} priority /><span>ALON <b>AI</b><small>OPERATOR DESK</small></span></a>
        <div className="sidebar-divider" />
        <p className="sidebar-label">Workspace</p>
        <nav className="operator-nav" aria-label="Workspace"><a className="operator-nav__active" href="#overview" aria-current="page"><span aria-hidden="true">◫</span> Overview</a><a href="#system"><span aria-hidden="true">◈</span> System status</a><a href="#activity"><span aria-hidden="true">≡</span> Activity log</a></nav>
        <p className="sidebar-label sidebar-label--tools">Navigate</p>
        <OperatorControls />
        <div className="sidebar-identity"><span className="identity-avatar" aria-hidden="true">{session.session.operator.display_name.slice(0, 1).toUpperCase()}</span><span><strong>{session.session.operator.display_name}</strong><small>Private operator</small></span></div>
      </aside>

      <main className="operator-main" id="main-content">
        <header className="topbar"><span className="breadcrumbs">Workspace <span aria-hidden="true">/</span> Overview</span><span className="private-session"><span aria-hidden="true" /> Private session</span></header>
        <div className="main-content">
          <div className="hero-heading"><div><p className="eyebrow">Control desk / 01</p><h1>One clear view of<br /><em>the work in motion.</em></h1><p className="hero-subtitle">A live account of system readiness and server-confirmed activity. Commands stay deliberate; every status has a source.</p></div><div className="hero-insignia" aria-hidden="true"><Image src="/alon-ai-mark.png" alt="" width={220} height={220} loading="eager" /></div></div>
          <div className="overview-grid"><StatusOverview initial={status} /><ActivityFeed initial={activity} /></div>
          <footer className="operator-footnote"><span>ALON AI / OPERATOR CONSOLE</span><span>All activity is read from the server</span></footer>
        </div>
      </main>
    </div>
  );
}
