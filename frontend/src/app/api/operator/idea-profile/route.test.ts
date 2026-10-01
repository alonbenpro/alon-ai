import { beforeEach, describe, expect, it, vi } from "vitest";

const { privateMutationProxy, privateProxy } = vi.hoisted(() => ({ privateMutationProxy: vi.fn(), privateProxy: vi.fn() }));
vi.mock("@/lib/operator/server", () => ({ privateMutationProxy, privateProxy }));

import { GET, POST } from "./route";

beforeEach(() => { privateMutationProxy.mockReset().mockResolvedValue(Response.json({ saved: true })); });

describe("operator idea profile proxy", () => {
  it("reads the saved profile through the authenticated private proxy", async () => {
    privateProxy.mockResolvedValue(Response.json({ profile: null }));
    expect((await GET()).status).toBe(200);
    expect(privateProxy).toHaveBeenCalledWith("/operator/idea-profile");
  });
  it("forwards the private same-origin profile command to the operator service", async () => {
    const request = new Request("http://localhost:3000/api/operator/idea-profile", {
      method: "POST", headers: { Origin: "http://localhost:3000", "Content-Type": "application/json" },
      body: JSON.stringify({ command_key: "key-1", profile: { display_name: "Alon" } }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(privateMutationProxy).toHaveBeenCalledWith("/operator/idea-profile", request);
  });
});
