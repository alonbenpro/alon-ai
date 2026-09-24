import { authProxy } from "@/lib/operator/server";

export async function POST(request: Request) {
  return authProxy("/auth/login", request);
}
