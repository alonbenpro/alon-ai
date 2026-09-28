import { privateMutationProxy } from "@/lib/operator/server";

export async function POST(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return privateMutationProxy(`/operator/agent-runs/${encodeURIComponent(runId)}/cancel`, request);
}
