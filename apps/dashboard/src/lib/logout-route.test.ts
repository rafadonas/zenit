import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/auth/logout/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const csrfToken = "a".repeat(64);

function logoutRequest(origin = "http://localhost:3000"): NextRequest {
  return new NextRequest("http://localhost:3000/api/auth/logout", {
    body: new URLSearchParams({ csrf_token: csrfToken }),
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-token`,
      Origin: origin,
    },
    method: "POST",
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard logout route", () => {
  it("revokes the bearer token before clearing the local cookies", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(logoutRequest());

    expect(apiFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/auth/logout",
      expect.objectContaining({
        headers: { Authorization: "Bearer signed-token" },
        method: "POST",
      }),
    );
    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?status=signed-out",
    );
    const cookies = response.headers.getSetCookie().join(";");
    expect(cookies).toContain(`${SESSION_COOKIE_NAME}=`);
    expect(cookies).toContain(`${CSRF_COOKIE_NAME}=`);
    expect(cookies).toContain("Max-Age=0");
  });

  it("clears local cookies and reports an unconfirmed remote revocation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const response = await POST(logoutRequest());

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?status=signed-out-local",
    );
    expect(response.headers.getSetCookie().join(";")).toContain("Max-Age=0");
  });

  it("rejects cross-origin logout before forwarding the token", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);

    const response = await POST(logoutRequest("http://attacker.test"));

    expect(response.status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
