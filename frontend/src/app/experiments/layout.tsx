import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { OperatorSidebar } from "@/components/operator/operator-sidebar";
import { getSession } from "@/lib/operator/server";

export default async function ExperimentsLayout({ children }: { children: ReactNode }) {
  const session = await getSession();
  if (session.kind === "unauthenticated") redirect("/login");
  if (session.kind === "unavailable") return <main className="access-unavailable"><div className="access-unavailable__panel"><span className="eyebrow">Access check unavailable</span><h1>We can’t verify this session.</h1><p>The operator service did not confirm access.</p><Link href="/">Retry access check</Link></div></main>;

  return <div className="operator-app">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <OperatorSidebar active="experiments" displayName={session.session.operator.display_name} />
    <main className="operator-main" id="main-content"><header className="topbar"><span className="breadcrumbs">Workspace <span aria-hidden="true">/</span> Experiments</span><span className="private-session"><span aria-hidden="true" /> Private session</span></header><div className="main-content">{children}</div></main>
  </div>;
}
