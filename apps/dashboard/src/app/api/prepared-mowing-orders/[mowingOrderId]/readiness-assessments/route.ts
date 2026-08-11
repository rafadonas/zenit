import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME, csrfTokensMatch, getDashboardSecurityConfig, isUuid,
  parsePreparedMowingReadinessSubmission, requestOriginMatches, SESSION_COOKIE_NAME,
} from "../../../../../lib/session-security";

interface RouteContext { params: Promise<{ mowingOrderId: string }>; }

function redirect(origin: string, status: string): NextResponse {
  const destination = new URL("/photo-reviews", origin);
  destination.searchParams.set("readiness", status);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin readiness request rejected" }, { status: 403 });
  }
  const { mowingOrderId } = await context.params;
  if (!isUuid(mowingOrderId)) return redirect(config.publicOrigin, "invalid");
  let form: FormData;
  try { form = await request.formData(); } catch { return redirect(config.publicOrigin, "invalid"); }
  const submission = parsePreparedMowingReadinessSubmission(form);
  if (!submission || !csrfTokensMatch(
    submission.csrfToken, request.cookies.get(CSRF_COOKIE_NAME)?.value,
  )) return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  const body = {
    resource_plan_id: submission.resourcePlanId,
    weather_result: submission.weatherResult,
    weather_source_reference: submission.weatherSourceReference,
    safety_result: submission.safetyResult,
    safety_source_reference: submission.safetySourceReference,
    assessment_rationale: submission.assessmentRationale,
    ...(submission.supersedesAssessmentId ? {
      supersedes_assessment_id: submission.supersedesAssessmentId,
    } : {}),
  };
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let upstream: Response;
  try {
    upstream = await fetch(
      `${baseUrl}/v1/prepared-mowing-orders/${mowingOrderId}/readiness-assessments`,
      {
        method: "POST", cache: "no-store", body: JSON.stringify(body),
        headers: {
          Authorization: `Bearer ${token}`, "Content-Type": "application/json",
          "Idempotency-Key": submission.idempotencyKey,
        },
      },
    );
  } catch { return redirect(config.publicOrigin, "service-unavailable"); }
  if (upstream.ok) return redirect(config.publicOrigin, "recorded");
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
