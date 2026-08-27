import { randomBytes } from "node:crypto";

import { NextResponse } from "next/server";

import { isAccessTokenContract } from "../../../../lib/auth-contracts";
import { setDashboardSessionCookies } from "../../../../lib/dashboard-cookies";
import {
  getDashboardSecurityConfig,
  getRequestHostOrigin,
  getRequestOrigin,
  requestOriginMatches,
} from "../../../../lib/session-security";

export const runtime = "nodejs";

function redirectToLogin(publicOrigin: string, error: string, requestOrigin?: string | null): NextResponse {
  const destination = new URL("/login", requestOrigin ?? publicOrigin);
  destination.searchParams.set("error", error);
  return NextResponse.redirect(destination, 303);
}

export async function POST(request: Request): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  const requestOrigin = getRequestOrigin(request);
  if (!requestOriginMatches(request, config.publicOrigin, config.appEnvironment)) {
    return NextResponse.json({ detail: "Cross-origin login rejected" }, { status: 403 });
  }
  const navigationOrigin =
    requestOrigin === "null"
      ? (getRequestHostOrigin(request) ?? config.publicOrigin)
      : (requestOrigin ?? config.publicOrigin);

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirectToLogin(config.publicOrigin, "invalid-request", navigationOrigin);
  }
  const email = form.get("email");
  const password = form.get("password");
  if (
    typeof email !== "string" ||
    typeof password !== "string" ||
    email.length < 3 ||
    email.length > 320 ||
    password.length < 1 ||
    password.length > 1024
  ) {
    return redirectToLogin(config.publicOrigin, "invalid-request", navigationOrigin);
  }

  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const credentials = new URLSearchParams({ username: email.trim(), password });
  let apiResponse: Response;
  try {
    apiResponse = await fetch(`${baseUrl}/v1/auth/token`, {
      body: credentials,
      cache: "no-store",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      method: "POST",
    });
  } catch {
    return redirectToLogin(config.publicOrigin, "service-unavailable", navigationOrigin);
  }
  if (!apiResponse.ok) {
    const error =
      apiResponse.status === 401
        ? "credentials"
        : apiResponse.status === 429
          ? "rate-limited"
          : "service-unavailable";
    return redirectToLogin(
      config.publicOrigin,
      error,
      navigationOrigin,
    );
  }

  const payload: unknown = await apiResponse.json();
  if (!isAccessTokenContract(payload)) {
    return redirectToLogin(config.publicOrigin, "service-unavailable", navigationOrigin);
  }

  const response = NextResponse.redirect(
    new URL("/recommendations?auth=signed-in", navigationOrigin),
    303,
  );
  setDashboardSessionCookies(
    response,
    config,
    payload.access_token,
    randomBytes(32).toString("hex"),
    payload.expires_in,
  );
  response.headers.set("Cache-Control", "no-store");
  return response;
}
