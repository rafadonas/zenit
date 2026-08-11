import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-mowing-orders/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const csrf = "a".repeat(64);

afterEach(() => vi.unstubAllGlobals());

describe("prepared mowing-order proxy", () => {
  it("forwards only an allowlisted CSRF-checked planning request", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrf,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      source_review_id: "20000000-0000-4000-8000-000000000001",
      planning_rationale: "Preparar planejamento sem liberar execução",
      authorizes_field_work: "true",
    });
    const request = new NextRequest("http://localhost:3000/api/prepared-mowing-orders", {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded", Origin: "http://localhost:3000",
        Cookie: `${CSRF_COOKIE_NAME}=${csrf}; ${SESSION_COOKIE_NAME}=signed-api-token`,
      },
    });
    expect((await POST(request)).status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      source_review_id: "20000000-0000-4000-8000-000000000001",
      planning_rationale: "Preparar planejamento sem liberar execução",
    });
  });

  it("rejects cross-origin before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest("http://localhost:3000/api/prepared-mowing-orders", {
      method: "POST", headers: { Origin: "http://attacker.test" },
    });
    expect((await POST(request)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
