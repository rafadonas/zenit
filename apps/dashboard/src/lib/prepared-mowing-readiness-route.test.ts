import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-mowing-orders/[mowingOrderId]/readiness-assessments/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const csrf = "a".repeat(64);
const orderId = "72000000-0000-4000-8000-000000000002";
const context = { params: Promise.resolve({ mowingOrderId: orderId }) };

afterEach(() => vi.unstubAllGlobals());

describe("prepared mowing readiness proxy", () => {
  it("forwards manual assessments without authorization fields", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrf, idempotency_key: "10000000-0000-4000-8000-000000000001",
      resource_plan_id: "72000000-0000-4000-8000-000000000003",
      weather_result: "clear", weather_source_reference: "Consulta manual",
      safety_result: "inconclusive", safety_source_reference: "Checklist incompleto",
      assessment_rationale: "Avaliação preparada", authorizes_field_work: "true",
    });
    const request = new NextRequest("http://localhost:3000/api/readiness", {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded", Origin: "http://localhost:3000",
        Cookie: `${CSRF_COOKIE_NAME}=${csrf}; ${SESSION_COOKIE_NAME}=signed-api-token`,
      },
    });
    expect((await POST(request, context)).status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      resource_plan_id: "72000000-0000-4000-8000-000000000003",
      weather_result: "clear", weather_source_reference: "Consulta manual",
      safety_result: "inconclusive", safety_source_reference: "Checklist incompleto",
      assessment_rationale: "Avaliação preparada",
    });
  });

  it("rejects cross-origin before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest("http://localhost:3000/api/readiness", {
      method: "POST", headers: { Origin: "http://attacker.test" },
    });
    expect((await POST(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
