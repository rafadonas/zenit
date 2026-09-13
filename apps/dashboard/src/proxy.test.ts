import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxy } from "./proxy";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("fixed dashboard proxy", () => {
  it("sends the root of a manager dashboard to the simplified overview", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "manager@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/overview");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(new NextRequest("http://localhost:3000/"));

    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/api/auth/fixed-session?return_to=%2Foverview",
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

  it("sends an existing fixed manager session from the root to its overview", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "manager@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/overview");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(
      new NextRequest("http://localhost:3000/", {
        headers: { cookie: "zenit_session=existing" },
      }),
    );

    expect(response.headers.get("location")).toBe("http://localhost:3000/overview");
  });

  it("renders the access explanation instead of looping when a fixed session is absent", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "manager@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/overview");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(
      new NextRequest("http://localhost:3000/login?error=service-unavailable"),
    );

    expect(response.headers.get("location")).toBeNull();
  });

  it("returns an existing fixed session from login to the configured workspace", () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "test");
    vi.stubEnv("DASHBOARD_FIXED_USER_EMAIL", "supervisor@example.com");
    vi.stubEnv("DASHBOARD_FIXED_HOME_PATH", "/mowing-photo-reviews");
    vi.stubEnv(
      "DASHBOARD_FIXED_SESSION_SECRET",
      "fixed-session-secret-that-is-long-enough",
    );

    const response = proxy(
      new NextRequest("http://localhost:3002/login", {
        headers: { cookie: "zenit_session=existing" },
      }),
    );

    expect(response.headers.get("location")).toBe(
      "http://localhost:3002/mowing-photo-reviews",
    );
  });
});
