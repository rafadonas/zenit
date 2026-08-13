import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-mowing-orders/[mowingOrderId]/post-service-summary/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const mowingOrderId = "98000000-0000-4000-8000-000000000001";
const csrfToken = "a".repeat(64);
const context = { params: Promise.resolve({ mowingOrderId }) };

afterEach(() => vi.unstubAllGlobals());

describe("mowing post-service summary dashboard proxy", () => {
  it("rejects a cross-origin request before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest(
      `http://localhost:3000/api/prepared-mowing-orders/${mowingOrderId}/post-service-summary`,
      { method: "POST", headers: { Origin: "http://attacker.test" } },
    );

    expect((await POST(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only a CSRF-checked rationale to the simulated summary endpoint", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrfToken,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      generation_rationale: "Consolidar pós-serviço simulado",
      eligible_for_official_reporting: "true",
      authorizes_field_work: "true",
    });
    const request = new NextRequest(
      `http://localhost:3000/api/prepared-mowing-orders/${mowingOrderId}/post-service-summary`,
      {
        method: "POST", body,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
          Origin: "http://localhost:3000",
        },
      },
    );

    const response = await POST(request, context);

    expect(response.status).toBe(303);
    const [url, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain(`/v1/prepared-mowing-orders/${mowingOrderId}/post-service-summary`);
    expect(JSON.parse(String(options.body))).toEqual({
      generation_rationale: "Consolidar pós-serviço simulado",
    });
    expect(options.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
  });
});
