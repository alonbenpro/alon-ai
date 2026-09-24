import { privateProxy } from "@/lib/operator/server";

export async function GET(request: Request) {
  return privateProxy("/operator/activity/events", request);
}
