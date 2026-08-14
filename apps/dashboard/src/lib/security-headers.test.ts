import { describe, expect, it } from "vitest";

import nextConfig, { dashboardSecurityHeaders } from "../../next.config";

describe("dashboard security headers", () => {
  it("applies the fail-closed browser baseline to every route", async () => {
    expect(nextConfig.poweredByHeader).toBe(false);
    expect(nextConfig.headers).toBeTypeOf("function");

    const rules = await nextConfig.headers!();
    expect(rules).toEqual([
      {
        source: "/:path*",
        headers: [...dashboardSecurityHeaders],
      },
    ]);
    expect(Object.fromEntries(dashboardSecurityHeaders.map(({ key, value }) => [key, value])))
      .toEqual({
        "Content-Security-Policy": "base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-DNS-Prefetch-Control": "off",
        "X-Frame-Options": "DENY",
      });
  });
});
