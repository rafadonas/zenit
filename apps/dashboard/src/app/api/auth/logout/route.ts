import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../lib/dashboard-cookies";
import {
  CSRF_COOKIE_NAME,
  csrfTokensMatch,
  getDashboardSecurityConfig,
  requestOriginMatches,
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

  const response = NextResponse.redirect(new URL("/login?status=signed-out", config.publicOrigin), 303);
  clearDashboardSessionCookies(response, config);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
