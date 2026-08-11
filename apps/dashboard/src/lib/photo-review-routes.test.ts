import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET as getMedia } from "../app/api/media/[photoId]/route";
import { POST as postReview } from "../app/api/media/[photoId]/reviews/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const photoId = "40000000-0000-4000-8000-000000000007";
const csrfToken = "a".repeat(64);
const context = { params: Promise.resolve({ photoId }) };

afterEach(() => vi.unstubAllGlobals());

describe("prepared photo dashboard proxies", () => {
  it("proxies exact allowlisted image content without exposing the bearer token", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response(new Uint8Array([0xff, 0xd8, 0xff]), {
      headers: { "Content-Type": "image/jpeg" }, status: 200,
    }));
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest(`http://localhost:3000/api/media/${photoId}`, {
      headers: { Cookie: `${SESSION_COOKIE_NAME}=signed-api-token` },
    });

    const response = await getMedia(request, context);

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store, private");
    expect(response.headers.get("x-zenit-data-status")).toBe("prepared");
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(options.headers).toMatchObject({ Authorization: "Bearer signed-api-token" });
    expect(response.headers.get("authorization")).toBeNull();
  });

  it("rejects cross-origin review before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest(`http://localhost:3000/api/media/${photoId}/reviews`, {
      method: "POST", headers: { Origin: "http://attacker.test" },
    });

    expect((await postReview(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only a CSRF-checked consistent review", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrfToken,
      idempotency_key: "10000000-0000-4000-8000-000000000001",
      decision: "accepted", quality_status: "accepted", ruler_status: "visible",
      reviewer_user_id: "forged",
    });
    const request = new NextRequest(`http://localhost:3000/api/media/${photoId}/reviews`, {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
        Origin: "http://localhost:3000",
      },
    });

    const response = await postReview(request, context);

    expect(response.status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      decision: "accepted", quality_status: "accepted", ruler_status: "visible",
    });
    expect(options.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
  });
});
