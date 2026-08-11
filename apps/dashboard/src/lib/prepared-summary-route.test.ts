import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST as postSummary } from "../app/api/work-orders/[workOrderId]/prepared-summary/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const workOrderId = "50000000-0000-4000-8000-000000000001";
const csrfToken = "a".repeat(64);
const context = { params: Promise.resolve({ workOrderId }) };

afterEach(() => vi.unstubAllGlobals());

describe("prepared summary dashboard proxy", () => {
  it("rejects a cross-origin request before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest(
      `http://localhost:3000/api/work-orders/${workOrderId}/prepared-summary`,
      { method: "POST", headers: { Origin: "http://attacker.test" } },
    );

    expect((await postSummary(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only the CSRF-checked rationale and server-side actor token", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrfToken,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      generation_rationale: "Consolidar retorno preparado",
      eligible_for_official_reporting: "true",
    });
    const request = new NextRequest(
      `http://localhost:3000/api/work-orders/${workOrderId}/prepared-summary`,
      {
        method: "POST", body,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
          Origin: "http://localhost:3000",
        },
      },
    );

    const response = await postSummary(request, context);

    expect(response.status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      generation_rationale: "Consolidar retorno preparado",
    });
    expect(options.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
  });
});
