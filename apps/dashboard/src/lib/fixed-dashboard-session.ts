export interface FixedDashboardSessionConfig {
  email: string;
  secret: string;
}

export function getFixedDashboardSessionConfig(
  environment: Readonly<Record<string, string | undefined>> = process.env,
): FixedDashboardSessionConfig | null {
  const email = environment.DASHBOARD_FIXED_USER_EMAIL?.trim().toLowerCase();
  const secret = environment.DASHBOARD_FIXED_SESSION_SECRET;
  if (!email && !secret) return null;
  if (!email || !secret) {
    throw new Error(
      "DASHBOARD_FIXED_USER_EMAIL and DASHBOARD_FIXED_SESSION_SECRET must be configured together",
    );
  }

  const appEnvironment = environment.DASHBOARD_APP_ENV ?? "development";
  if (!["development", "test", "demo"].includes(appEnvironment)) {
    throw new Error("fixed dashboard sessions are restricted to development, test, and demo");
  }
  if (email.length < 3 || email.length > 320 || !email.includes("@")) {
    throw new Error("DASHBOARD_FIXED_USER_EMAIL is invalid");
  }
  if (secret.length < 32) {
    throw new Error("DASHBOARD_FIXED_SESSION_SECRET must contain at least 32 characters");
  }
  return { email, secret };
}

export function safeReturnPath(value: string | null): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    value.length > 2048
  ) {
    return "/";
  }
  return value;
}
