import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "../app/api/auth/fixed-session/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("fixed dashboard session route", () => {
  it("creates strict cookies for the configured user and returns to the requested page", async () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_PUBLIC_ORIGIN", "http://localhost:3002");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "supervisor@example.com");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );
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

    const response = await GET(
      new NextRequest(
        "http://localhost:3002/api/auth/fixed-session?return_to=%2Fphoto-reviews%3Freview%3Drecorded",
      ),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3002/photo-reviews?review=recorded",
    );
    expect(apiFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/auth/fixed-session",
      expect.objectContaining({
        body: JSON.stringify({ email: "supervisor@example.com" }),
        method: "POST",
      }),
    );
    const cookies = response.headers.getSetCookie().join(";");
    expect(cookies).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(cookies).toContain(`${CSRF_COOKIE_NAME}=`);
    expect(cookies).toContain("HttpOnly");
    expect(cookies).toContain("SameSite=strict");
  });

  it("returns to an explanatory login screen without exposing an upstream failure", async () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "manager@example.com");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("private detail", { status: 401 })));

    const response = await GET(
      new NextRequest("http://localhost:3000/api/auth/fixed-session"),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?error=service-unavailable",
    );
    expect(await response.text()).not.toContain("private detail");
  });
});
