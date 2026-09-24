import { afterEach, describe, expect, it, vi } from "vitest";

import { authProxy } from "@/lib/operator/server";

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
