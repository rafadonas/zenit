import { type NextRequest, NextResponse } from "next/server";

import { clearDashboardSessionCookies } from "../../../../lib/dashboard-cookies";
import { getDashboardSecurityConfig, isUuid, SESSION_COOKIE_NAME } from "../../../../lib/session-security";

interface RouteContext { params: Promise<{ photoId: string }>; }

export async function GET(request: NextRequest, context: RouteContext): Promise<Response> {
  const config = getDashboardSecurityConfig();
  const { photoId } = await context.params;
  if (!isUuid(photoId)) return NextResponse.json({ detail: "Invalid photo" }, { status: 404 });
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/v1/media/${photoId}`, {
      cache: "no-store", headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    return NextResponse.json({ detail: "Media unavailable" }, { status: 503 });
  }
  if (upstream.status === 401) {
    const response = NextResponse.json({ detail: "Session expired" }, { status: 401 });
    clearDashboardSessionCookies(response, config);
    return response;
  }
  if (!upstream.ok) return NextResponse.json({ detail: "Media unavailable" }, { status: upstream.status });
  const contentType = upstream.headers.get("content-type");
  if (contentType !== "image/jpeg" && contentType !== "image/png") {
    return NextResponse.json({ detail: "Unsafe media response" }, { status: 502 });
  }
  return new Response(await upstream.arrayBuffer(), {
    headers: {
      "Cache-Control": "no-store, private",
      "Content-Type": contentType,
      "X-Content-Type-Options": "nosniff",
      "X-Zenit-Data-Status": "prepared",
      "X-Zenit-Eligible-For-Official-Reporting": "false",
    },
  });
}
