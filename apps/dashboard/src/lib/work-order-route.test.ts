import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/work-orders/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const csrfToken = "a".repeat(64);

function orderRequest(options?: { origin?: string; csrf?: string }): NextRequest {
  return new NextRequest("http://localhost:3000/api/work-orders", {
    body: new URLSearchParams({
      csrf_token: options?.csrf ?? csrfToken,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      source_review_id: "20000000-0000-4000-8000-000000000001",
      planning_rationale: "Preparar três pontos para inspeção",
      created_by_user_id: "forged-actor",
      authorizes_field_work: "true",
    }),
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
      Origin: options?.origin ?? "http://localhost:3000",
    },
    method: "POST",
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("prepared inspection-order proxy", () => {
  it("rejects cross-origin requests before calling the API", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(orderRequest({ origin: "http://attacker.test" }));

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("rejects a mismatched CSRF token before calling the API", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(orderRequest({ csrf: "b".repeat(64) }));

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only the source review and rationale with the server token", async () => {
    const apiFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authorizes_field_work: false }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(orderRequest());

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/recommendations?order=prepared",
    );
    const [, request] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(request.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
    expect(JSON.parse(String(request.body))).toEqual({
      source_review_id: "20000000-0000-4000-8000-000000000001",
      planning_rationale: "Preparar três pontos para inspeção",
    });
  });
});
