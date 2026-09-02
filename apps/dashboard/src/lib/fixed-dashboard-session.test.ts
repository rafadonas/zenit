import { afterEach, describe, expect, it, vi } from "vitest";

import { getFixedDashboardSessionConfig, safeReturnPath } from "./fixed-dashboard-session";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("fixed dashboard session configuration", () => {
  it("is disabled when no fixed identity is configured", () => {
    expect(getFixedDashboardSessionConfig({ DASHBOARD_APP_ENV: "development" })).toBeNull();
  });

  it("accepts a complete local fixed identity", () => {
    expect(
      getFixedDashboardSessionConfig({
      DASHBOARD_APP_ENV: "demo",
      DASHBOARD_FIXED_HOME_PATH: "/photo-reviews",
        DASHBOARD_FIXED_SESSION_SECRET: "fixed-session-secret-that-is-long-enough",
        DASHBOARD_FIXED_USER_EMAIL: " Manager@Example.Test ",
      }),
    ).toEqual({
      email: "manager@example.test",
      homePath: "/photo-reviews",
      secret: "fixed-session-secret-that-is-long-enough",
    });
  });

  it("fails closed outside safe environments", () => {
    expect(() =>
      getFixedDashboardSessionConfig({
        DASHBOARD_APP_ENV: "production",
        DASHBOARD_FIXED_SESSION_SECRET: "fixed-session-secret-that-is-long-enough",
        DASHBOARD_FIXED_USER_EMAIL: "manager@example.test",
      }),
    ).toThrow(/restricted/);
  });

  it("allows only local return paths", () => {
    expect(safeReturnPath("/photo-reviews?review=recorded")).toBe(
      "/photo-reviews?review=recorded",
    );
    expect(safeReturnPath("//attacker.test/path")).toBe("/");
    expect(safeReturnPath("/\\attacker.test/path")).toBe("/");
    expect(safeReturnPath("https://attacker.test/path")).toBe("/");
  });
});
