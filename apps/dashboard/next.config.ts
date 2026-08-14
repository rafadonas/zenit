import type { NextConfig } from "next";

export const dashboardSecurityHeaders = [
  { key: "Content-Security-Policy", value: "base-uri 'self'; form-action 'self'; frame-ancestors 'none'" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=()" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  { key: "X-Frame-Options", value: "DENY" },
] as const;

const nextConfig: NextConfig = {
  agentRules: false,
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [...dashboardSecurityHeaders],
      },
    ];
  },
  experimental: {
    // The TypeScript API is stable across the supported Node runtimes and avoids
    // a cross-spawn stdout issue observed with the CLI on this workstation.
    useTypeScriptCli: false,
  },
};

export default nextConfig;
