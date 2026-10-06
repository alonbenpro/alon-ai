import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchCasePanel } from "@/components/experiments/research-case";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("retained market research case", () => {
  it("shows findings, source references, coverage, and gaps without claiming completion", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
      experiment_id: "exp-1", progress: "PARTIAL", finding_count: 2,
      limitations: ["Only public sources checked"], subjects: [{
        subject: { artifact_id: "candidate-1", kind: "IDEA_CANDIDATE", version: 1, role: "RESEARCH_SUBJECT" },
        mode: "CANDIDATE", current: true,
        coverage: [{ dimension: "CUSTOMER_PAIN", status: "SUPPORTED", finding_ids: ["finding-1"] }],
        gaps: ["PRICING"], findings: [{
          artifact: { artifact_id: "finding-1", version: 1 },
          observation: { dimension: "CUSTOMER_PAIN", claim: "Staff spend time on reminders",
            finding: "A clinic job post describes manual follow-up", evidence_status: "SUPPORTED",
            limitations: ["One clinic"], step_key: "step-1" },
          sources: [{ reference: { kind: "RETAINED_CONTENT", retained_id: "source-1", field: "description" },
            availability: "REFERENCE_ONLY" }],
        }, {
          artifact: { artifact_id: "finding-2", version: 1 },
          observation: { dimension: "ALTERNATIVES", claim: "Alternative 1",
            finding: "Manual reminders might suffice", evidence_status: "INCONCLUSIVE",
            limitations: ["Agent-generated hypothesis; not an observed market fact."], step_key: "step-2" },
          sources: [],
        }],
      }],
    })));
    render(<ResearchCasePanel experimentId="exp-1" />);
    expect(await screen.findByText(/Partial research record/)).toBeInTheDocument();
    expect(screen.getByText("A clinic job post describes manual follow-up")).toBeInTheDocument();
    expect(screen.getByText(/Open gaps: pricing/)).toBeInTheDocument();
    expect(screen.getByText("Only public sources checked")).toBeInTheDocument();
    expect(within(screen.getByText(/Source references \(1\)/).closest("details")!).getByText(/source-1/)).toBeInTheDocument();
    expect(screen.getByText(/Agent analysis without a retained source/)).toBeInTheDocument();
    expect(screen.queryByText(/research complete/i)).not.toBeInTheDocument();
  });

  it("shows unavailable evidence instead of a false complete state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ detail: "not found" }, { status: 404 })));
    render(<ResearchCasePanel experimentId="exp-1" />);
    expect(await screen.findByText(/Research case is unavailable/)).toBeInTheDocument();
  });

  it("links only current Firecrawl originals and keeps expired, Brave, and unsafe URLs unavailable", async () => {
    const sources = [
      { reference: { kind: "RETAINED_CONTENT", retained_id: "firecrawl-current" },
        availability: "CURRENT_SOURCE", provider: "FIRECRAWL", url: "https://clinic.example.org/research",
        title: "Clinic research page", available_until: "2099-01-01T00:00:00Z" },
      { reference: { kind: "RETAINED_CONTENT", retained_id: "firecrawl-host" },
        availability: "CURRENT_SOURCE", provider: "FIRECRAWL", url: "https://journal.example.org/study",
        title: null, available_until: "2099-01-01T00:00:00Z" },
      { reference: { kind: "RETAINED_CONTENT", retained_id: "firecrawl-expired" },
        availability: "CURRENT_SOURCE", provider: "FIRECRAWL", url: "https://clinic.example.org/expired",
        title: "Expired page", available_until: "2000-01-01T00:00:00Z" },
      { reference: { kind: "RETAINED_CONTENT", retained_id: "reference-only" },
        availability: "REFERENCE_ONLY", provider: "FIRECRAWL", url: "https://clinic.example.org/old",
        title: "Reference only", available_until: "2099-01-01T00:00:00Z" },
      { reference: { kind: "RETAINED_CONTENT", retained_id: "brave-source" },
        availability: "CURRENT_SOURCE", provider: "BRAVE", url: "https://brave.example.org/result",
        title: "Brave result", available_until: "2099-01-01T00:00:00Z" },
      { reference: { kind: "RETAINED_CONTENT", retained_id: "unsafe-source" },
        availability: "CURRENT_SOURCE", provider: "FIRECRAWL", url: "javascript:alert(1)",
        title: "Unsafe source", available_until: "2099-01-01T00:00:00Z" },
    ];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ experiment_id: "exp-1", progress: "PARTIAL",
      finding_count: 1, limitations: [], subjects: [{
        subject: { artifact_id: "candidate-1", kind: "IDEA_CANDIDATE", version: 1, role: "RESEARCH_SUBJECT" },
        mode: "CANDIDATE", current: true, coverage: [], gaps: [], findings: [{
          artifact: { artifact_id: "finding-1", version: 1 },
          observation: { dimension: "DEMAND", claim: "Possible demand", finding: "Limited signal",
            evidence_status: "INCONCLUSIVE", limitations: [], step_key: "step-1" }, sources,
        }],
      }],
    })));
    render(<ResearchCasePanel experimentId="exp-1" />);
    const details = (await screen.findByText("Source references (6)")).closest("details")!;
    const link = within(details).getByRole("link", { name: "Clinic research page" });
    expect(link).toHaveAttribute("href", "https://clinic.example.org/research");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(details).getByRole("link", { name: "journal.example.org" })).toHaveAttribute("href", "https://journal.example.org/study");
    expect(within(details).getAllByText(/Original source unavailable/)).toHaveLength(4);
    expect(within(details).getByText(/brave-source/)).toBeInTheDocument();
    expect(within(details).getByText(/firecrawl-expired/)).toBeInTheDocument();
    expect(within(details).getByText(/unsafe-source/)).toBeInTheDocument();
    expect(within(details).getAllByRole("link")).toHaveLength(2);
  });
});
