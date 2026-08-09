import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME,
  csrfTokensMatch,
  getDashboardSecurityConfig,
  parsePreparedInspectionOrderSubmission,
  requestOriginMatches,
  SESSION_COOKIE_NAME,
} from "../../../lib/session-security";

function redirectWithStatus(publicOrigin: string, status: string): NextResponse {
  const destination = new URL("/recommendations", publicOrigin);
  destination.searchParams.set("order", status);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin order request rejected" }, { status: 403 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirectWithStatus(config.publicOrigin, "invalid");
  }
  const submission = parsePreparedInspectionOrderSubmission(form);
  const csrfCookie = request.cookies.get(CSRF_COOKIE_NAME)?.value;
  if (!submission || !csrfTokensMatch(submission.csrfToken, csrfCookie)) {
    return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  }

  const accessToken = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!accessToken) {
    return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  }

  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let apiResponse: Response;
  try {
    apiResponse = await fetch(`${baseUrl}/v1/work-orders`, {
      body: JSON.stringify({
        source_review_id: submission.sourceReviewId,
        planning_rationale: submission.planningRationale,
      }),
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "Idempotency-Key": submission.idempotencyKey,
      },
      method: "POST",
    });
  } catch {
    return redirectWithStatus(config.publicOrigin, "service-unavailable");
  }

  if (apiResponse.ok) return redirectWithStatus(config.publicOrigin, "prepared");
  if (apiResponse.status === 401) {
    const response = NextResponse.redirect(
      new URL("/login?error=session", config.publicOrigin),
      303,
    );
    clearDashboardSessionCookies(response, config);
    return response;
  }
  const statuses: Record<number, string> = {
    403: "forbidden",
    404: "missing-review",
    409: "conflict",
    422: "invalid",
  };
  return redirectWithStatus(config.publicOrigin, statuses[apiResponse.status] ?? "service-unavailable");
}
