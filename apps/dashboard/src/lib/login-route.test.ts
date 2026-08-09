import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/auth/session/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

function loginRequest(origin = "http://localhost:3000"): NextRequest {
  return new NextRequest("http://localhost:3000/api/auth/session", {
    body: new URLSearchParams({
      email: "manager@example.test",
      password: "local-test-password",
    }),
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Origin: origin,
    },
    method: "POST",
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard login route", () => {
  it("rejects cross-origin login before forwarding credentials", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(loginRequest("http://attacker.test"));

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("stores the bearer token only in a strict HttpOnly session cookie", async () => {
    const apiFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "signed-token-value-that-is-long-enough",
          expires_in: 1800,
          token_type: "bearer",
          user: { id: "user-1" },
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      ),
    );
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(loginRequest());

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/recommendations?auth=signed-in",
    );
    const cookies = response.headers.getSetCookie().join(";");
    expect(cookies).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(cookies).toContain(`${CSRF_COOKIE_NAME}=`);
    expect(cookies).toContain("HttpOnly");
    expect(cookies).toContain("SameSite=strict");
  });
});
