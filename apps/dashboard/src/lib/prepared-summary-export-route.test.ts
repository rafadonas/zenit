import { createHash } from "node:crypto";

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST as postExport } from "../app/api/prepared-inspection-summaries/[summaryId]/exports/route";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

const summaryId = "50000000-0000-4000-8000-000000000002";
const csrfToken = "a".repeat(64);
const context = { params: Promise.resolve({ summaryId }) };

function request(): NextRequest {
  const body = new URLSearchParams({
    csrf_token: csrfToken,
    idempotency_key: "10000000-0000-4000-8000-000000000001",
    export_purpose: "Compartilhar resultado preparado",
    eligible_for_official_reporting: "true",
  });
  return new NextRequest(
    `http://localhost:3000/api/prepared-inspection-summaries/${summaryId}/exports`,
    {
      method: "POST", body,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Cookie: `${CSRF_COOKIE_NAME}=${csrfToken}; ${SESSION_COOKIE_NAME}=signed-api-token`,
        Origin: "http://localhost:3000",
      },
    },
  );
}

function safeUpstream(content = "export_notice,summary_id\r\nPREPARED,summary\r\n"): Response {
  const checksum = createHash("sha256").update(content).digest("hex");
  return new Response(content, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "X-Zenit-Checksum-SHA256": checksum,
      "X-Zenit-Export-Schema-Version": "prepared-inspection-summary-csv-v1",
      "X-Zenit-Data-Status": "prepared",
      "X-Zenit-Location-Status": "simulated",
      "X-Zenit-Eligible-For-Official-Reporting": "false",
      "X-Zenit-Authorizes-Field-Work": "false",
    },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("prepared summary CSV dashboard proxy", () => {
  it("rejects a cross-origin export before forwarding", async () => {
    const apiFetch = vi.fn();
    vi.stubGlobal("fetch", apiFetch);
    const crossOrigin = request();
    crossOrigin.headers.set("origin", "http://attacker.test");

    expect((await postExport(crossOrigin, context)).status).toBe(403);
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("forwards only the purpose and returns a verified non-official CSV", async () => {
    const apiFetch = vi.fn().mockResolvedValue(safeUpstream());
    vi.stubGlobal("fetch", apiFetch);

    const response = await postExport(request(), context);

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("text/csv; charset=utf-8");
    expect(response.headers.get("cache-control")).toBe("no-store, private");
    expect(response.headers.get("x-zenit-eligible-for-official-reporting")).toBe("false");
    expect(response.headers.get("authorization")).toBeNull();
    const [, options] = apiFetch.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(options.body))).toEqual({
      export_purpose: "Compartilhar resultado preparado",
    });
    expect(options.headers).toMatchObject({
      Authorization: "Bearer signed-api-token",
      "Idempotency-Key": "10000000-0000-4000-8000-000000000001",
    });
  });

  it("fails closed when upstream omits safety headers or has a bad checksum", async () => {
    const missingLabels = vi.fn().mockResolvedValue(new Response("csv", {
      status: 200, headers: { "Content-Type": "text/csv" },
    }));
    vi.stubGlobal("fetch", missingLabels);
    let response = await postExport(request(), context);
    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toContain("export=unsafe-response");

    const corrupt = safeUpstream();
    corrupt.headers.set("x-zenit-checksum-sha256", "0".repeat(64));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(corrupt));
    response = await postExport(request(), context);
    expect(response.headers.get("location")).toContain("export=unsafe-response");
  });
});
