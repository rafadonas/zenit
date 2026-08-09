import { cookies } from "next/headers";

import { isAuthenticatedContext, type AuthenticatedContext } from "./auth-contracts";
import { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME } from "./session-security";

export interface DashboardSession extends AuthenticatedContext {
  csrfToken: string;
}

export async function loadDashboardSession(): Promise<DashboardSession | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const csrfToken = cookieStore.get(CSRF_COOKIE_NAME)?.value;
  if (!accessToken || !csrfToken) return null;

  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${baseUrl}/v1/auth/me`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) return null;
    const payload: unknown = await response.json();
    if (!isAuthenticatedContext(payload)) return null;
    return { ...payload, csrfToken };
  } catch {
    return null;
  }
}
