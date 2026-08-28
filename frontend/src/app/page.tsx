import Image from "next/image";

import { ApiStatus } from "@/components/api-status";
import { QueryProvider } from "@/components/query-provider";

export default function Home() {
  return (
    <main className="app-shell">
      <div className="viewport-frame">
        <header className="brand">
          <Image
            alt=""
            aria-hidden="true"
            height={40}
            priority
            src="/alon-ai-mark.png"
            width={40}
          />
          <span>Alon AI</span>
        </header>

        <div className="dashboard">
          <svg
            aria-hidden="true"
            className="journey-route"
            focusable="false"
            preserveAspectRatio="none"
            viewBox="0 0 1320 684"
          >
            <path d="M12 640 H360 Q380 640 380 620 V590 Q380 570 400 570 H500 Q520 570 520 550 V520 Q520 500 540 500 H700 Q720 500 720 480 V25 Q720 1 744 1 H820" />
            <circle cx="12" cy="640" r="7" />
          </svg>

          <section className="introduction">
            <h1>
              <span>Validate ideas.</span>{" "}
              <span>Prove demand.</span>{" "}
              <span>Keep control.</span>
            </h1>
            <p>
              A private operating system for researching offers, qualifying
              prospects, sending guarded Gmail outreach, and learning from real
              replies.
            </p>
          </section>

          <QueryProvider>
            <ApiStatus />
          </QueryProvider>
        </div>
      </div>
    </main>
  );
}
