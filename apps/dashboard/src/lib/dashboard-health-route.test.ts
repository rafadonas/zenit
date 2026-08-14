import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "../app/api/health/route";

const healthyApiPayload = {
  checks: {
    database: { required: true, status: "ok" },
    object_storage: { required: true, status: "ok" },
    queue: { required: false, status: "not_configured" },
  },
  status: "ok",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard health route", () => {
  it("reports ready only after validating the API dependency contract", async () => {
    const apiFetch = vi.fn().mockResolvedValue(Response.json(healthyApiPayload));
    vi.stubGlobal("fetch", apiFetch);

    const response = await GET();

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    await expect(response.json()).resolves.toEqual({
      checks: { api: { required: true, status: "ok" } },
      service: "zenit-dashboard",
      status: "ok",
    });
    expect(apiFetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("fails closed when the API health request is unsuccessful", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    const response = await GET();

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toMatchObject({
      checks: { api: { required: true, status: "degraded" } },
      status: "degraded",
    });
  });

  it("fails closed when the API readiness payload is incomplete", async () => {
    const incomplete = structuredClone(healthyApiPayload);
    incomplete.checks.object_storage.status = "unknown";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(incomplete)));

    const response = await GET();

    expect(response.status).toBe(503);
  });

  it("sanitizes API connection failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private upstream detail")));

    const response = await GET();

    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain("private upstream detail");
  });
});
