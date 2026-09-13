import { randomBytes } from "node:crypto";

import { type NextRequest, NextResponse } from "next/server";

import { isAccessTokenContract } from "../../../../lib/auth-contracts";
import { setDashboardSessionCookies } from "../../../../lib/dashboard-cookies";
import {
  getFixedDashboardSessionConfig,
  safeReturnPath,
} from "../../../../lib/fixed-dashboard-session";
import { getDashboardSecurityConfig } from "../../../../lib/session-security";

export const runtime = "nodejs";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const fixedConfig = getFixedDashboardSessionConfig();
  if (!fixedConfig) {
    return NextResponse.json({ detail: "Fixed dashboard session is disabled" }, { status: 404 });
  }

  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const securityConfig = getDashboardSecurityConfig();
  const unavailable = () => NextResponse.redirect(
    new URL("/login?error=service-unavailable", securityConfig.publicOrigin),
    303,
  );
  let apiResponse: Response;
  try {
    apiResponse = await fetch(`${baseUrl}/v1/auth/fixed-session`, {
      body: JSON.stringify({ email: fixedConfig.email }),
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Zenit-Fixed-Session-Secret": fixedConfig.secret,
      },
      method: "POST",
    });
  } catch {
    return unavailable();
  }
  if (!apiResponse.ok) {
    return unavailable();
  }

  const payload: unknown = await apiResponse.json();
  if (!isAccessTokenContract(payload)) {
    return unavailable();
  }

  const requestedReturnPath = safeReturnPath(request.nextUrl.searchParams.get("return_to"));
  const returnPath = requestedReturnPath === "/" ? fixedConfig.homePath : requestedReturnPath;
  const response = NextResponse.redirect(new URL(returnPath, securityConfig.publicOrigin), 303);
  setDashboardSessionCookies(
    response,
    securityConfig,
    payload.access_token,
    randomBytes(32).toString("hex"),
    payload.expires_in,
  );
  response.headers.set("Cache-Control", "no-store");
  return response;
}
