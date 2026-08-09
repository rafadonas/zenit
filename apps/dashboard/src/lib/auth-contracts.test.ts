import { describe, expect, it } from "vitest";

import { isAccessTokenContract, isAuthenticatedContext } from "./auth-contracts";

describe("dashboard authentication contracts", () => {
  it("accepts a bounded bearer-token response", () => {
    expect(
      isAccessTokenContract({
        access_token: "signed-token-value-that-is-long-enough",
        token_type: "bearer",
        expires_in: 1800,
        user: { id: "ignored-by-session-route" },
      }),
    ).toBe(true);
  });

  it("rejects unbounded token lifetimes", () => {
    expect(
      isAccessTokenContract({
        access_token: "signed-token-value-that-is-long-enough",
        token_type: "bearer",
        expires_in: 604800,
      }),
    ).toBe(false);
  });

  it("accepts only scoped reviewer roles with provenance status", () => {
    expect(
      isAuthenticatedContext({
        user: {
          id: "user-1",
          email: "manager@example.test",
          display_name: "MVP Manager",
        },
        road_roles: [{ road_code: "SP021", role: "manager", data_status: "prepared" }],
      }),
    ).toBe(true);
    expect(
      isAuthenticatedContext({
        user: {
          id: "user-1",
          email: "manager@example.test",
          display_name: "MVP Manager",
        },
        road_roles: [{ road_code: "SP021", role: "admin", data_status: "prepared" }],
      }),
    ).toBe(false);
  });
});
