import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME, csrfTokensMatch, getDashboardSecurityConfig, isUuid,
  parsePreparedProposalSubmission, requestOriginMatches, SESSION_COOKIE_NAME,
} from "../../../../../lib/session-security";

interface RouteContext { params: Promise<{ summaryId: string }>; }

function resolveReturnPath(value: FormDataEntryValue | null): string {
  return value === "/photo-reviews" ? "/photo-reviews" : "/mowing-post-service-summaries";
}

function redirect(origin: string, path: string, status: string): NextResponse {
  const destination = new URL(path, origin);
  destination.searchParams.set("mowing_exception", status);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json(
      { detail: "Cross-origin mowing exception request rejected" },
      { status: 403 },
    );
  }
  const { summaryId } = await context.params;
  if (!isUuid(summaryId)) {
    return redirect(config.publicOrigin, "/mowing-post-service-summaries", "invalid");
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirect(config.publicOrigin, "/mowing-post-service-summaries", "invalid");
  }
  const returnPath = resolveReturnPath(form.get("return_path"));
  const submission = parsePreparedProposalSubmission(form);
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
    upstream = await fetch(`${baseUrl}/v1/prepared-mowing-post-service-summaries/${summaryId}/exceptions`, {
      method: "POST", cache: "no-store",
      body: JSON.stringify({ creation_rationale: submission.creationRationale }),
      headers: {
        Authorization: `Bearer ${token}`, "Content-Type": "application/json",
        "Idempotency-Key": submission.idempotencyKey,
      },
    });
  } catch { return redirect(config.publicOrigin, returnPath, "service-unavailable"); }
  if (upstream.ok) return redirect(config.publicOrigin, returnPath, "created");
  if (upstream.status === 401) {
    const response = NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
    clearDashboardSessionCookies(response, config);
    return response;
  }
  const statuses: Record<number, string> = {
    403: "forbidden", 404: "missing", 409: "conflict", 422: "invalid", 503: "service-unavailable",
  };
  return redirect(
    config.publicOrigin,
    returnPath,
    statuses[upstream.status] ?? "service-unavailable",
  );
}
