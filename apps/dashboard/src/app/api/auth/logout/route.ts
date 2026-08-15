import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME,
  csrfTokensMatch,
  getDashboardSecurityConfig,
  requestOriginMatches,
  SESSION_COOKIE_NAME,
} from "../../../../lib/session-security";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) {
    return NextResponse.json({ detail: "Cross-origin logout rejected" }, { status: 403 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ detail: "Invalid logout request" }, { status: 400 });
  }
  const csrf = form.get("csrf_token");
  const cookieToken = request.cookies.get(CSRF_COOKIE_NAME)?.value;
  if (!csrfTokensMatch(typeof csrf === "string" ? csrf : null, cookieToken)) {
    return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  }

  const accessToken = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  let remotelyRevoked = accessToken === undefined;
  if (accessToken) {
    const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
    try {
      const apiResponse = await fetch(`${baseUrl}/v1/auth/logout`, {
        cache: "no-store",
        headers: { Authorization: `Bearer ${accessToken}` },
        method: "POST",
      });
      remotelyRevoked = apiResponse.status === 204 || apiResponse.status === 401;
    } catch {
      remotelyRevoked = false;
    }
  }

  const logoutStatus = remotelyRevoked ? "signed-out" : "signed-out-local";
  const response = NextResponse.redirect(
    new URL(`/login?status=${logoutStatus}`, config.publicOrigin),
    303,
  );
  clearDashboardSessionCookies(response, config);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
