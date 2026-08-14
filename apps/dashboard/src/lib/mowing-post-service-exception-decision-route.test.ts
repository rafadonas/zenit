import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-mowing-post-service-exceptions/[exceptionId]/decisions/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const exceptionId = "99000000-0000-4000-8000-000000000002";
const csrfToken = "a".repeat(64);
const context = { params: Promise.resolve({ exceptionId }) };

afterEach(() => vi.unstubAllGlobals());

describe("mowing post-service exception review dashboard proxy", () => {
  it("rejects cross-origin review requests before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest(
      `http://localhost:3000/api/prepared-mowing-post-service-exceptions/${exceptionId}/decisions`,
      { method: "POST", headers: { Origin: "http://attacker.test" } },
    );

    expect((await POST(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only the CSRF-checked exception decision", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrfToken,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      decision: "adjusted",
      adjusted_recommendation: "inspect_follow_up",
      rationale: "Registrar inspeção de seguimento após revisão humana.",
      supersedes_review_id: "99000000-0000-4000-8000-000000000099",
      eligible_for_official_reporting: "true",
    });
    const request = new NextRequest(
      `http://localhost:3000/api/prepared-mowing-post-service-exceptions/${exceptionId}/decisions`,
      {
        method: "POST",
        body,
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
    expect(url).toContain(`/v1/prepared-mowing-post-service-exceptions/${exceptionId}/decisions`);
    expect(JSON.parse(String(options.body))).toEqual({
      decision: "adjusted",
      adjusted_recommendation: "inspect_follow_up",
      rationale: "Registrar inspeção de seguimento após revisão humana.",
      supersedes_review_id: "99000000-0000-4000-8000-000000000099",
    });
    expect(options.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
  });
});
