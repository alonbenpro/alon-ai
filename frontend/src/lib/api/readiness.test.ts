import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api/client";
import { fetchReadiness } from "@/lib/api/readiness";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: vi.fn(),
  },
}));

const mockedGet = vi.mocked(apiClient.GET);

describe("fetchReadiness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns the typed readiness response on success", async () => {
    mockedGet.mockResolvedValue({
      data: { database: "up", status: "ready" },
      response: new Response(null, { status: 200 }),
    });

    await expect(fetchReadiness()).resolves.toEqual({
      database: "up",
      status: "ready",
    });
  });

  it("throws the stable readiness error when the API rejects readiness", async () => {
    mockedGet.mockResolvedValue({
      error: { database: "down", status: "not_ready" },
      response: new Response(null, { status: 503 }),
    });

    await expect(fetchReadiness()).rejects.toThrow(
      "API readiness check failed",
    );
  });
});
