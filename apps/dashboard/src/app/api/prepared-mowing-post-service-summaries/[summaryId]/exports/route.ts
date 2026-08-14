import { createHash } from "node:crypto";

import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME, csrfTokensMatch, getDashboardSecurityConfig, isUuid,
  parsePreparedSummaryExportSubmission, requestOriginMatches, SESSION_COOKIE_NAME,
} from "../../../../../lib/session-security";

const MAX_EXPORT_BYTES = 1_048_576;
const EXPORT_SCHEMA_VERSION = "simulated-mowing-post-service-summary-csv-v1";

interface RouteContext { params: Promise<{ summaryId: string }>; }

function resolveReturnPath(value: FormDataEntryValue | null): string {
  return value === "/photo-reviews" ? "/photo-reviews" : "/mowing-post-service-summaries";
}

function redirect(origin: string, path: string, status: string): NextResponse {
  const destination = new URL(path, origin);
  destination.searchParams.set("export", status);
  return NextResponse.redirect(destination, 303);
}

function hasSafeExportHeaders(response: Response): boolean {
  return response.headers.get("content-type")?.split(";", 1)[0]?.trim() === "text/csv" &&
    response.headers.get("x-zenit-export-schema-version") === EXPORT_SCHEMA_VERSION &&
    response.headers.get("x-zenit-data-status") === "simulated" &&
    response.headers.get("x-zenit-location-status") === "not_collected" &&
    response.headers.get("x-zenit-eligible-for-official-reporting") === "false" &&
    response.headers.get("x-zenit-authorizes-field-work") === "false";
}

export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin mowing export rejected" }, { status: 403 });
  }
  const { summaryId } = await context.params;
  if (!isUuid(summaryId)) return redirect(config.publicOrigin, "/mowing-post-service-summaries", "invalid");
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirect(config.publicOrigin, "/mowing-post-service-summaries", "invalid");
  }
  const returnPath = resolveReturnPath(form.get("return_path"));
  const submission = parsePreparedSummaryExportSubmission(form);
  if (!submission || !csrfTokensMatch(
    submission.csrfToken, request.cookies.get(CSRF_COOKIE_NAME)?.value,
  )) {
    return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  }
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/v1/prepared-mowing-post-service-summaries/${summaryId}/exports`, {
      method: "POST", cache: "no-store",
      body: JSON.stringify({ export_purpose: submission.exportPurpose }),
      headers: {
        Authorization: `Bearer ${token}`, "Content-Type": "application/json",
        "Idempotency-Key": submission.idempotencyKey,
      },
    });
  } catch {
    return redirect(config.publicOrigin, returnPath, "service-unavailable");
  }
  if (upstream.status === 401) {
    const response = NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
    clearDashboardSessionCookies(response, config);
    return response;
  }
  if (!upstream.ok) {
    const statuses: Record<number, string> = {
      404: "missing", 409: "conflict", 422: "invalid", 503: "service-unavailable",
    };
    return redirect(
      config.publicOrigin,
      returnPath,
      statuses[upstream.status] ?? "service-unavailable",
    );
  }
  if (!hasSafeExportHeaders(upstream)) {
    return redirect(config.publicOrigin, returnPath, "unsafe-response");
  }
  const content = new Uint8Array(await upstream.arrayBuffer());
  if (content.byteLength === 0 || content.byteLength > MAX_EXPORT_BYTES) {
    return redirect(config.publicOrigin, returnPath, "unsafe-response");
  }
  const checksum = upstream.headers.get("x-zenit-checksum-sha256");
  const calculated = createHash("sha256").update(content).digest("hex");
  if (checksum !== calculated) {
    return redirect(config.publicOrigin, returnPath, "unsafe-response");
  }
  return new NextResponse(content, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="zenit-simulated-mowing-summary-${summaryId}.csv"`,
      "Cache-Control": "no-store, private",
      "X-Content-Type-Options": "nosniff",
      "X-Zenit-Checksum-SHA256": checksum,
      "X-Zenit-Export-Schema-Version": EXPORT_SCHEMA_VERSION,
      "X-Zenit-Data-Status": "simulated",
      "X-Zenit-Location-Status": "not_collected",
      "X-Zenit-Eligible-For-Official-Reporting": "false",
      "X-Zenit-Authorizes-Field-Work": "false",
    },
  });
}
