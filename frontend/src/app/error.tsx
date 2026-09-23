"use client";

export default function ErrorPage({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <main className="access-unavailable"><div className="access-unavailable__panel"><span className="eyebrow">View unavailable</span><h1>This view could not load.</h1><p>The system did not confirm a result. Retry the view to check again.</p><button type="button" onClick={retry}>Retry view</button></div></main>;
}
