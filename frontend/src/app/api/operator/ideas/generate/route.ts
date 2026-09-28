import { privateMutationProxy } from "@/lib/operator/server";

export async function POST(request: Request) {
  return privateMutationProxy("/operator/ideas/generate", request);
}
