import { privateMutationProxy } from "@/lib/operator/server";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return privateMutationProxy(`/operator/experiments/${encodeURIComponent(id)}/idea-revisions`, request);
}
