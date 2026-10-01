import { privateMutationProxy, privateProxy } from "@/lib/operator/server";

export async function GET() {
  return privateProxy("/operator/idea-profile");
}

export async function POST(request: Request) {
  return privateMutationProxy("/operator/idea-profile", request);
}
