import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME, csrfTokensMatch, getDashboardSecurityConfig,
  parsePreparedMowingOrderSubmission, requestOriginMatches, SESSION_COOKIE_NAME,
} from "../../../lib/session-security";

function redirect(origin: string, status: string): NextResponse {
  const destination = new URL("/photo-reviews", origin);
  destination.searchParams.set("mowing_order", status);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin mowing-order request rejected" }, { status: 403 });
  }
  let form: FormData;
  try { form = await request.formData(); } catch { return redirect(config.publicOrigin, "invalid"); }
  const submission = parsePreparedMowingOrderSubmission(form);
  if (!submission || !csrfTokensMatch(
    submission.csrfToken, request.cookies.get(CSRF_COOKIE_NAME)?.value,
  )) return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/v1/prepared-mowing-orders`, {
      method: "POST", cache: "no-store",
      body: JSON.stringify({
        source_review_id: submission.sourceReviewId,
        planning_rationale: submission.planningRationale,
      }),
      headers: {
        Authorization: `Bearer ${token}`, "Content-Type": "application/json",
        "Idempotency-Key": submission.idempotencyKey,
      },
    });
  } catch { return redirect(config.publicOrigin, "service-unavailable"); }
  if (upstream.ok) return redirect(config.publicOrigin, "created");
  if (upstream.status === 401) {
    const response = NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
    clearDashboardSessionCookies(response, config);
    return response;
  }
  const statuses: Record<number, string> = {
    403: "forbidden", 404: "missing", 409: "conflict", 422: "invalid",
    503: "service-unavailable",
  };
  return redirect(config.publicOrigin, statuses[upstream.status] ?? "service-unavailable");
}
