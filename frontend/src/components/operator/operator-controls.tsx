"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const destinations = [
  { title: "Overview", detail: "Top of the control desk", href: "#overview" },
  { title: "System status", detail: "Health, readiness, and recorded work", href: "#system" },
  { title: "Activity log", detail: "Server-confirmed activity", href: "#activity" },
];

export function OperatorControls() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [motionOff, setMotionOff] = useState(false);
  const [logoutError, setLogoutError] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    previousFocus.current?.focus();
  }, []);

  const navigate = (href: string) => {
    close();
    window.history.pushState(null, "", href);
    document.getElementById(href.slice(1))?.scrollIntoView();
  };

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const saved = window.localStorage.getItem("alon-motion-off") === "true";
      setMotionOff(saved);
      document.documentElement.dataset.motion = saved ? "off" : "auto";
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        previousFocus.current = document.activeElement as HTMLElement;
        setOpen(true);
      } else if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  useEffect(() => { if (open) input.current?.focus(); }, [open]);

  useEffect(() => {
    if (!open) return;
    const prior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prior; };
  }, [open]);

  const toggleMotion = () => {
    const next = !motionOff;
    setMotionOff(next);
    document.documentElement.dataset.motion = next ? "off" : "auto";
    window.localStorage.setItem("alon-motion-off", String(next));
  };

  const logout = async () => {
    setLogoutError(false);
    try {
      const response = await fetch("/api/auth/logout", { method: "POST", cache: "no-store" });
      if (!response.ok) throw new Error("Logout was not confirmed");
      window.location.replace("/login");
    } catch { setLogoutError(true); }
  };

  const matches = destinations.filter((item) => `${item.title} ${item.detail}`.toLowerCase().includes(query.toLowerCase()));

  return (
    <>
      <button type="button" className="command-trigger" onClick={() => { previousFocus.current = document.activeElement as HTMLElement; setOpen(true); }} aria-label="Open command palette">
        <span aria-hidden="true">⌕</span><span>Jump to…</span><kbd>⌘ K</kbd>
      </button>
      <div className="sidebar-footer">
        <button type="button" className="sidebar-action" onClick={toggleMotion} aria-pressed={motionOff}><span aria-hidden="true">◌</span> Motion {motionOff ? "off" : "on"}</button>
        <button type="button" className="sidebar-action" onClick={() => void logout()}><span aria-hidden="true">↗</span> Sign out</button>
        {logoutError && <p className="sidebar-error" role="alert">Sign out was not confirmed. Try again.</p>}
      </div>
      {open && createPortal(<div className="palette-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
        <div role="dialog" aria-modal="true" aria-labelledby="palette-title" className="command-palette" onKeyDown={(event) => {
          if (event.key !== "Tab") return;
          const focusables = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("input, a"));
          const first = focusables[0];
          const last = focusables.at(-1);
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }}>
          <label id="palette-title" htmlFor="palette-input">Navigate the control desk</label>
          <input ref={input} id="palette-input" type="search" placeholder="Find a view…" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => {
            if (event.key === "Escape") { event.preventDefault(); close(); }
            if (event.key === "Enter" && matches[0]) { event.preventDefault(); navigate(matches[0].href); }
          }} />
          <div className="palette-results">
            {matches.length ? matches.map((item) => <a key={item.href} href={item.href} onClick={(event) => { event.preventDefault(); navigate(item.href); }}><span><strong>{item.title}</strong><small>{item.detail}</small></span><span aria-hidden="true">↗</span></a>) : <p>No matching views</p>}
          </div>
          <div className="palette-hint">Esc to close · Enter to open first result</div>
        </div>
      </div>, document.body)}
    </>
  );
}
