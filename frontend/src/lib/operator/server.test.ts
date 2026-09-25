import { afterEach, describe, expect, it, vi } from "vitest";

import { authProxy, getExperimentRuntime, privateMutationProxy } from "@/lib/operator/server";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => undefined }) }));

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

describe("authProxy origin boundary", () => {
  it("uses the configured public origin behind a local container port mapping", async () => {
    vi.stubEnv("ALON_AI_FRONTEND_ORIGIN", "http://localhost:13000");
    const backend = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", backend);
    const request = new Request("http://localhost:3000/api/auth/login", {
      method: "POST",
      headers: { Origin: "http://localhost:13000" },
      body: JSON.stringify({ password: "disposable-test" }),
    });

    const response = await authProxy("/auth/login", request);

    expect(response.status).toBe(204);
    expect(backend).toHaveBeenCalledOnce();
    const init = backend.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("Origin")).toBe("http://localhost:13000");
  });

  it("rejects a different origin before forwarding credentials", async () => {
    vi.stubEnv("ALON_AI_FRONTEND_ORIGIN", "http://localhost:13000");
    const backend = vi.fn();
    vi.stubGlobal("fetch", backend);
    const request = new Request("http://localhost:3000/api/auth/login", {
      method: "POST",
      headers: { Origin: "https://untrusted.example" },
      body: JSON.stringify({ password: "disposable-test" }),
    });

    expect((await authProxy("/auth/login", request)).status).toBe(403);
    expect(backend).not.toHaveBeenCalled();
  });
});

describe("experiment mutation proxy", () => {
  it("rejects a cross-origin request without forwarding experiment data", async () => {
    const backend = vi.fn();
    vi.stubGlobal("fetch", backend);
    const request = new Request("http://localhost:3000/api/operator/experiments", {
      method: "POST", headers: { Origin: "https://attacker.example" },
      body: JSON.stringify({ idea_seed: "Private idea" }),
    });

    expect((await privateMutationProxy("/operator/experiments", request)).status).toBe(403);
    expect(backend).not.toHaveBeenCalled();
  });

  it("forwards a same-origin JSON command and returns server confirmation", async () => {
    const backend = vi.fn().mockResolvedValue(Response.json({ state: "AWAITING_REFINEMENT" }, { status: 201 }));
    vi.stubGlobal("fetch", backend);
    const body = JSON.stringify({ idea_seed: "Private idea", command_key: "key-1" });
    const request = new Request("http://localhost:3000/api/operator/experiments", {
      method: "POST", headers: { Origin: "http://localhost:3000", "Content-Type": "application/json" }, body,
    });

    const response = await privateMutationProxy("/operator/experiments", request);

    expect(response.status).toBe(201);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store, max-age=0");
    expect(await response.json()).toEqual({ state: "AWAITING_REFINEMENT" });
    expect(backend).toHaveBeenCalledOnce();
    expect(new URL(backend.mock.calls[0][0]).pathname).toBe("/operator/experiments");
    expect(backend.mock.calls[0][1]).toMatchObject({ method: "POST", body });
  });
});

describe("experiment runtime readiness", () => {
  it("reads only the server-confirmed runtime mode and availability", async () => {
    const backend = vi.fn().mockResolvedValue(Response.json({
      provider_mode: "live", ready: true, internal_secret: "must-not-leak",
    }));
    vi.stubGlobal("fetch", backend);

    expect(await getExperimentRuntime()).toEqual({ provider_mode: "live", ready: true });
    expect(new URL(backend.mock.calls[0][0]).pathname).toBe("/operator/experiments/runtime");
  });

  it("fails closed when the readiness endpoint is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect(await getExperimentRuntime()).toBeNull();
  });
});
