import { privateProxy } from "@/lib/operator/server";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return privateProxy(`/operator/experiments/${encodeURIComponent(id)}/research-case`, request);
}
