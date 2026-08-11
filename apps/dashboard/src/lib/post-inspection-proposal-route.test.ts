import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "../app/api/prepared-inspection-summaries/[summaryId]/post-inspection-proposal/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const summaryId = "60000000-0000-4000-8000-000000000001";
const csrf = "a".repeat(64);
const context = { params: Promise.resolve({ summaryId }) };

afterEach(() => vi.unstubAllGlobals());

describe("prepared post-inspection proposal proxy", () => {
  it("forwards only a CSRF-checked rationale", async () => {
    const apiFetch = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", apiFetch);
    const body = new URLSearchParams({
      csrf_token: csrf, idempotency_key: "10000000-0000-4000-8000-000000000001",
      creation_rationale: "Aplicar regra preparada", authorizes_field_work: "true",
    });
    const request = new NextRequest(`http://localhost:3000/api/proposal`, {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded", Origin: "http://localhost:3000",
        Cookie: `${CSRF_COOKIE_NAME}=${csrf}; ${SESSION_COOKIE_NAME}=signed-api-token`,
      },
    });

    expect((await POST(request, context)).status).toBe(303);
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({ creation_rationale: "Aplicar regra preparada" });
    expect(options.headers).toMatchObject({ Authorization: "Bearer signed-api-token" });
  });

  it("rejects cross-origin before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const request = new NextRequest("http://localhost:3000/api/proposal", {
      method: "POST", headers: { Origin: "http://attacker.test" },
    });
    expect((await POST(request, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
