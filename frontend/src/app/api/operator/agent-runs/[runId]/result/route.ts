import { privateProxy } from "@/lib/operator/server";

export async function GET(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return privateProxy(`/operator/agent-runs/${encodeURIComponent(runId)}/result`, request);
}
