import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-mowing-orders/[mowingOrderId]/resource-plans/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const csrf = "a".repeat(64);
const mowingOrderId = "70000000-0000-4000-8000-000000000005";
const context = { params: Promise.resolve({ mowingOrderId }) };

afterEach(() => vi.unstubAllGlobals());

describe("prepared mowing resource-plan proxy", () => {
  it("forwards only unverified candidate references", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrf,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      team_reference: "Equipe candidata A",
      equipment_reference: "Equipamento candidato B",
      planning_rationale: "Planejar recursos pendentes de validação",
      authorizes_field_work: "true",
    });
    const request = new NextRequest("http://localhost:3000/api/resource-plan", {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded", Origin: "http://localhost:3000",
        Cookie: `${CSRF_COOKIE_NAME}=${csrf}; ${SESSION_COOKIE_NAME}=signed-api-token`,
      },
    });
    expect((await POST(request, context)).status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      team_reference: "Equipe candidata A",
      equipment_reference: "Equipamento candidato B",
      planning_rationale: "Planejar recursos pendentes de validação",
    });
  });

  it("rejects cross-origin before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest("http://localhost:3000/api/resource-plan", {
      method: "POST", headers: { Origin: "http://attacker.test" },
    });
    expect((await POST(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
