import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/recommendations/[analysisId]/decisions/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const analysisId = "20000000-0000-4000-8000-000000000001";
const csrfToken = "a".repeat(64);

function decisionRequest(options?: { origin?: string; csrf?: string }): NextRequest {
  const body = new URLSearchParams({
    csrf_token: options?.csrf ?? csrfToken,
    decision: "accepted",
    idempotency_key: "10000000-0000-4000-8000-000000000001",
    reviewer_subject: "forged-actor",
  });
  return new NextRequest(
    `http://localhost:3000/api/recommendations/${analysisId}/decisions`,
    {
      body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
        Origin: options?.origin ?? "http://localhost:3000",
      },
      method: "POST",
    },
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("recommendation decision proxy", () => {
  it("rejects cross-origin requests before calling the API", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(decisionRequest({ origin: "http://attacker.test" }), {
      params: Promise.resolve({ analysisId }),
    });

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("rejects a mismatched CSRF token before calling the API", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(decisionRequest({ csrf: "b".repeat(64) }), {
      params: Promise.resolve({ analysisId }),
    });

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only allowlisted fields with the server-held bearer token", async () => {
    const apiFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authorizes_field_work: false }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(decisionRequest(), {
      params: Promise.resolve({ analysisId }),
    });

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/recommendations?decision=recorded",
    );
    expect(apiFetch).toHaveBeenCalledOnce();
    const [, request] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(request.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
    expect(JSON.parse(String(request.body))).toEqual({ decision: "accepted" });
  });
});
