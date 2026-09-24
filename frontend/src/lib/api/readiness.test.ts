import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchReadiness } from "@/lib/api/readiness";

const mockGet = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({ apiClient: { GET: mockGet } }));

describe("fetchReadiness", () => {
  beforeEach(() => mockGet.mockReset());

  it("returns the typed readiness response on success", async () => {
    mockGet.mockResolvedValue({
      data: { database: "up", status: "ready" },
      response: new Response(null, { status: 200 }),
    });

    await expect(fetchReadiness()).resolves.toEqual({
      database: "up",
      status: "ready",
    });
  });

  it("throws the stable readiness error when the API rejects readiness", async () => {
    mockGet.mockResolvedValue({
      error: { database: "down", status: "not_ready" },
      response: new Response(null, { status: 503 }),
    });

    await expect(fetchReadiness()).rejects.toThrow(
      "API readiness check failed",
    );
  });
});
