import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "./proxy";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("fixed dashboard proxy", () => {
  it("sends the root of a manager dashboard to recommendations", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "manager@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/recommendations");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(new NextRequest("http://localhost:3000/"));

    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/api/auth/fixed-session?return_to=%2Frecommendations",
    );
  });

  it("sends the root of a supervisor dashboard to post-service photo review", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "supervisor@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/mowing-photo-reviews");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(new NextRequest("http://localhost:3002/"));

    expect(response.headers.get("location")).toBe(
      "http://localhost:3002/api/auth/fixed-session?return_to=%2Fmowing-photo-reviews",
    );
  });
});
