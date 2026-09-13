import { type NextRequest, NextResponse } from "next/server";

import { getFixedDashboardSessionConfig } from "./lib/fixed-dashboard-session";
import { SESSION_COOKIE_NAME } from "./lib/session-security";

export function proxy(request: NextRequest): NextResponse {
  const fixedConfig = getFixedDashboardSessionConfig();
  if (!fixedConfig) return NextResponse.next();

  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE_NAME)?.value);
  if (hasSession && request.nextUrl.pathname === "/" && fixedConfig.homePath !== "/") {
    return NextResponse.redirect(new URL(fixedConfig.homePath, request.url));
  }
  if (hasSession && request.nextUrl.pathname === "/login") {
    return NextResponse.redirect(new URL(fixedConfig.homePath, request.url));
  }
  if (hasSession || request.nextUrl.pathname === "/login") return NextResponse.next();

  const destination = request.nextUrl.clone();
  destination.pathname = "/api/auth/fixed-session";
  destination.search = "";
  const returnPath = request.nextUrl.pathname === "/"
    ? fixedConfig.homePath
    : `${request.nextUrl.pathname}${request.nextUrl.search}`;
  destination.searchParams.set("return_to", returnPath);
  return NextResponse.redirect(destination);
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
