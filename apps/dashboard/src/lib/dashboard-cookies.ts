import type { NextResponse } from "next/server";

import {
  CSRF_COOKIE_NAME,
  type DashboardSecurityConfig,
  SESSION_COOKIE_NAME,
} from "./session-security";

export function setDashboardSessionCookies(
  response: NextResponse,
  config: DashboardSecurityConfig,
  accessToken: string,
  csrfToken: string,
  maxAge: number,
): void {
  response.cookies.set(SESSION_COOKIE_NAME, accessToken, {
    httpOnly: true,
    maxAge,
    path: "/",
    sameSite: "strict",
    secure: config.secureCookies,
  });
  response.cookies.set(CSRF_COOKIE_NAME, csrfToken, {
    httpOnly: false,
    maxAge,
    path: "/",
    sameSite: "strict",
    secure: config.secureCookies,
  });
}

export function clearDashboardSessionCookies(
  response: NextResponse,
  config: DashboardSecurityConfig,
): void {
  for (const name of [SESSION_COOKIE_NAME, CSRF_COOKIE_NAME]) {
    response.cookies.set(name, "", {
      httpOnly: name === SESSION_COOKIE_NAME,
      maxAge: 0,
      path: "/",
      sameSite: "strict",
      secure: config.secureCookies,
    });
  }
}
