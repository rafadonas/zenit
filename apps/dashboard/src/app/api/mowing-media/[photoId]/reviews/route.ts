import { type NextRequest, NextResponse } from "next/server";
import { clearDashboardSessionCookies } from "../../../../../lib/dashboard-cookies";
import { CSRF_COOKIE_NAME, csrfTokensMatch, getDashboardSecurityConfig, isUuid, parsePhotoReviewSubmission, requestOriginMatches, SESSION_COOKIE_NAME } from "../../../../../lib/session-security";
interface RouteContext { params: Promise<{ photoId: string }>; }
function redirect(origin: string, status: string): NextResponse { const destination = new URL("/mowing-photo-reviews", origin); destination.searchParams.set("review", status); return NextResponse.redirect(destination, 303); }
export async function POST(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const config = getDashboardSecurityConfig();
  if (!requestOriginMatches(request.headers.get("origin"), config.publicOrigin)) return NextResponse.json({ detail: "Cross-origin review rejected" }, { status: 403 });
  const { photoId } = await context.params;
  if (!isUuid(photoId)) return redirect(config.publicOrigin, "invalid");
  let form: FormData; try { form = await request.formData(); } catch { return redirect(config.publicOrigin, "invalid"); }
  const submission = parsePhotoReviewSubmission(form);
  if (!submission || !csrfTokensMatch(submission.csrfToken, request.cookies.get(CSRF_COOKIE_NAME)?.value)) return NextResponse.json({ detail: "CSRF validation failed" }, { status: 403 });
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303);
  const body = { decision: submission.decision, quality_status: submission.qualityStatus, ruler_status: submission.rulerStatus, ...(submission.rationale ? { rationale: submission.rationale } : {}), ...(submission.supersedesReviewId ? { supersedes_review_id: submission.supersedesReviewId } : {}) };
  let upstream: Response; try { upstream = await fetch(`${process.env.INTERNAL_API_URL ?? "http://localhost:8000"}/v1/mowing-media/${photoId}/reviews`, { method: "POST", cache: "no-store", body: JSON.stringify(body), headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": submission.idempotencyKey } }); } catch { return redirect(config.publicOrigin, "service-unavailable"); }
  if (upstream.ok) return redirect(config.publicOrigin, "recorded");
  if (upstream.status === 401) { const response = NextResponse.redirect(new URL("/login?error=session", config.publicOrigin), 303); clearDashboardSessionCookies(response, config); return response; }
  const statuses: Record<number, string> = { 403: "forbidden", 404: "missing", 409: "conflict", 422: "invalid" }; return redirect(config.publicOrigin, statuses[upstream.status] ?? "service-unavailable");
}
