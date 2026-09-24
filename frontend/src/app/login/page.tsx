import Image from "next/image";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/operator/login-form";
import { getSession } from "@/lib/operator/server";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const session = await getSession();
  if (session.kind === "authenticated") redirect("/");

  return <main className="login-page">
    <div className="login-masthead"><Image src="/alon-ai-mark.png" alt="" width={38} height={38} priority /><span>ALON <b>AI</b></span><small>PRIVATE OPERATOR SYSTEM</small></div>
    <div className="login-grid">
      <section className="login-editorial" aria-labelledby="login-thesis"><p className="eyebrow">A controlled workspace</p><h1 id="login-thesis">Clarity before<br /><em>action.</em></h1><p>Research, outreach, and learning move through one private control desk. Every result is verified before it becomes a claim.</p><div className="login-orbit" aria-hidden="true"><span className="login-orbit__one" /><span className="login-orbit__two" /><span className="login-orbit__center" /></div><div className="login-editorial__footer">DESIGNED FOR ONE OPERATOR <span>↗</span></div></section>
      <section className="login-panel" aria-labelledby="login-title"><div className="login-panel__top"><span className="login-panel__index">01 / ACCESS</span><span className="login-panel__lock" aria-hidden="true">◇</span></div><div><p className="eyebrow">Authorized access</p><h2 id="login-title">Enter the desk.</h2><p className="login-panel__copy">Sign in with your operator password to see the current system state.</p><LoginForm /></div><div className="login-panel__bottom">Your session is private and expires when revoked.</div></section>
    </div>
  </main>;
}
