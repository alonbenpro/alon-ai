import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { getSession } from "@/lib/operator/server";

export default async function ExperimentsLayout({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (session.kind === "unauthenticated") redirect("/login");
  if (session.kind === "unavailable") return <main className="access-unavailable"><div className="access-unavailable__panel"><span className="eyebrow">Access check unavailable</span><h1>We can’t verify this session.</h1><p>The operator service did not confirm access.</p><Link href="/">Retry access check</Link></div></main>;

  return <div className="operator-app">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="operator-sidebar" aria-label="Primary navigation">
      <Link className="operator-brand" href="/" aria-label="Alon AI overview"><Image src="/alon-ai-mark.png" alt="" width={42} height={42} priority /><span>ALON <b>AI</b><small>OPERATOR DESK</small></span></Link>
      <div className="sidebar-divider" /><p className="sidebar-label">Workspace</p>
      <nav className="operator-nav" aria-label="Workspace"><Link href="/"><span aria-hidden="true">◫</span> Overview</Link><Link className="operator-nav__active" href="/experiments/new" aria-current="page"><span aria-hidden="true">◇</span> New experiment</Link></nav>
      <div className="sidebar-identity"><span className="identity-avatar" aria-hidden="true">{session.session.operator.display_name.slice(0, 1).toUpperCase()}</span><span><strong>{session.session.operator.display_name}</strong><small>Private operator</small></span></div>
    </aside>
    <main className="operator-main" id="main-content"><header className="topbar"><span className="breadcrumbs">Workspace <span aria-hidden="true">/</span> Experiments</span><span className="private-session"><span aria-hidden="true" /> Private session</span></header><div className="main-content">{children}</div></main>
  </div>;
}
