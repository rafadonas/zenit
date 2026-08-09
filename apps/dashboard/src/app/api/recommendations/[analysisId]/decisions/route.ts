import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME,
  csrfTokensMatch,
  getDashboardSecurityConfig,
  isUuid,
  parseDecisionSubmission,
  requestOriginMatches,
  SESSION_COOKIE_NAME,
} from "../../../../../lib/session-security";

interface RouteContext {
  params: Promise<{ analysisId: string }>;
}

function redirectWithStatus(publicOrigin: string, status: string): NextResponse {
  const destination = new URL("/recommendations", publicOrigin);
  destination.searchParams.set("decision", status);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin decision rejected" }, { status: 403 });
  }

  const { analysisId } = await context.params;
  if (!isUuid(analysisId)) {
    return redirectWithStatus(config.publicOrigin, "invalid");
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirectWithStatus(config.publicOrigin, "invalid");
  }
  const submission = parseDecisionSubmission(form);
  const csrfCookie = request.cookies.get(CSRF_COOKIE_NAME)?.value;
  if (!submission || !csrfTokensMatch(submission.csrfToken, csrfCookie)) {
    return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  }

  const accessToken = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!accessToken) {
    return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  }

  const body = {
    decision: submission.decision,
    ...(submission.adjustedRecommendation
      ? { adjusted_recommendation: submission.adjustedRecommendation }
      : {}),
    ...(submission.rationale ? { rationale: submission.rationale } : {}),
    ...(submission.supersedesReviewId
      ? { supersedes_review_id: submission.supersedesReviewId }
      : {}),
  };
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let apiResponse: Response;
  try {
    apiResponse = await fetch(`${baseUrl}/v1/recommendations/${analysisId}/decisions`, {
      body: JSON.stringify(body),
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

  if (apiResponse.ok) return redirectWithStatus(config.publicOrigin, "recorded");
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
    404: "missing",
    409: "conflict",
    422: "invalid",
  };
  return redirectWithStatus(config.publicOrigin, statuses[apiResponse.status] ?? "service-unavailable");
}
