import "server-only";

import { cookies } from "next/headers";

import type { components } from "@/lib/api/schema";

const apiOrigin = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const privateHeaders = {
  "Cache-Control": "private, no-store, max-age=0",
  Vary: "Cookie",
};

export type OperatorSession = components["schemas"]["SessionResponse"] & {
  authenticated: true;
};

export type SessionResult =
  | { kind: "authenticated"; session: OperatorSession }
  | { kind: "unauthenticated" }
  | { kind: "unavailable" };

export async function backendFetch(path: string, init: RequestInit = {}) {
  const sessionCookie = (await cookies()).get("alon_ai_session")?.value;
  const headers = new Headers(init.headers);
  if (sessionCookie) headers.set("Cookie", `alon_ai_session=${sessionCookie}`);
  return fetch(new URL(path, apiOrigin), {
    ...init,
    headers,
    cache: "no-store",
    redirect: "manual",
  });
}

export async function getSession(): Promise<SessionResult> {
  try {
    const response = await backendFetch("/auth/session");
    if (response.status === 401 || response.status === 403) return { kind: "unauthenticated" };
    if (!response.ok) return { kind: "unavailable" };
    const value: unknown = await response.json();
    if (
      typeof value === "object" && value !== null &&
      "authenticated" in value && value.authenticated === true &&
      "operator" in value && typeof value.operator === "object" && value.operator !== null &&
      "id" in value.operator && typeof value.operator.id === "string" &&
      "display_name" in value.operator && typeof value.operator.display_name === "string"
    ) {
      return { kind: "authenticated", session: value as OperatorSession };
    }
  } catch {
    // An absent API is an unknown session, never permission to render private data.
  }
  return { kind: "unavailable" };
}

export async function getExperimentRuntime(): Promise<{
  provider_mode: "disabled" | "fake" | "live";
  ready: boolean;
} | null> {
  try {
    const response = await backendFetch("/operator/experiments/runtime");
    if (!response.ok) return null;
    const value: unknown = await response.json();
    if (typeof value !== "object" || value === null ||
      !("provider_mode" in value) || !("ready" in value) ||
      !["disabled", "fake", "live"].includes(String(value.provider_mode)) ||
      typeof value.ready !== "boolean") return null;
    return { provider_mode: value.provider_mode as "disabled" | "fake" | "live", ready: value.ready };
  } catch {
    return null;
  }
}

function operatorOrigin(request: Request) {
  const configured = process.env.ALON_AI_FRONTEND_ORIGIN;
  return configured ? new URL(configured).origin : new URL(request.url).origin;
}

export function isSameOrigin(request: Request) {
  const origin = request.headers.get("origin");
  return origin === operatorOrigin(request);
}

export async function privateProxy(path: string, request?: Request) {
  try {
    const response = await backendFetch(path, request ? { signal: request.signal } : {});
    return new Response(response.status === 204 ? null : response.body, {
      status: response.status,
      headers: {
        ...privateHeaders,
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return Response.json({ detail: "Service unavailable" }, { status: 503, headers: privateHeaders });
  }
}

export async function authProxy(path: string, request: Request) {
  if (!isSameOrigin(request)) {
    return Response.json({ detail: "Origin not allowed" }, { status: 403, headers: privateHeaders });
  }
  try {
    const response = await backendFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: operatorOrigin(request) },
      body: path.endsWith("/login") ? await request.text() : undefined,
      signal: request.signal,
    });
    const headers = new Headers(privateHeaders);
    headers.set("Content-Type", response.headers.get("Content-Type") ?? "application/json");
    for (const cookie of response.headers.getSetCookie()) headers.append("Set-Cookie", cookie);
    return new Response(response.status === 204 ? null : response.body, { status: response.status, headers });
  } catch {
    return Response.json({ detail: "Service unavailable" }, { status: 503, headers: privateHeaders });
  }
}

export async function privateMutationProxy(path: string, request: Request) {
  if (!isSameOrigin(request)) {
    return Response.json({ detail: "Origin not allowed" }, { status: 403, headers: privateHeaders });
  }
  try {
    const response = await backendFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: operatorOrigin(request) },
      body: await request.text(),
      signal: request.signal,
    });
    return new Response(response.status === 204 ? null : response.body, {
      status: response.status,
      headers: {
        ...privateHeaders,
        "Content-Type": response.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return Response.json({ detail: "Service unavailable" }, { status: 503, headers: privateHeaders });
  }
}
