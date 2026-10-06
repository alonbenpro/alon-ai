"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { OperatorControls } from "@/components/operator/operator-controls";

type OperatorSidebarProps = {
  active: "overview" | "experiments";
  displayName: string;
};

export function OperatorSidebar({ active, displayName }: OperatorSidebarProps) {
  const onOverview = active === "overview";
  const onProfile = usePathname() === "/experiments/profile";

  return <aside className="operator-sidebar" aria-label="Primary navigation">
    <Link className="operator-brand" href="/" aria-label="Alon AI overview"><Image src="/alon-ai-mark.png" alt="" width={42} height={42} priority /><span>ALON <b>AI</b><small>OPERATOR DESK</small></span></Link>
    <div className="sidebar-divider" />
    <p className="sidebar-label">Workspace</p>
    <nav className="operator-nav" aria-label="Workspace">
      <Link className={onOverview ? "operator-nav__active" : undefined} href={onOverview ? "#overview" : "/"} aria-current={onOverview ? "page" : undefined}><span aria-hidden="true">◫</span> Overview</Link>
      <Link className={!onOverview && !onProfile ? "operator-nav__active" : undefined} href="/experiments/new" aria-current={!onOverview && !onProfile ? "page" : undefined}><span aria-hidden="true">◇</span> New experiment</Link>
      <Link className={onProfile ? "operator-nav__active" : undefined} aria-current={onProfile ? "page" : undefined} href="/experiments/profile"><span aria-hidden="true">◉</span> Operator profile</Link>
      <Link href={onOverview ? "#system" : "/#system"}><span aria-hidden="true">◈</span> System status</Link>
      <Link href={onOverview ? "#activity" : "/#activity"}><span aria-hidden="true">≡</span> Activity log</Link>
    </nav>
    <p className="sidebar-label sidebar-label--tools">Navigate</p>
    <OperatorControls onOverview={onOverview} />
    <div className="sidebar-identity"><span className="identity-avatar" aria-hidden="true">{displayName.slice(0, 1).toUpperCase()}</span><span><strong>{displayName}</strong><small>Private operator</small></span></div>
  </aside>;
}
