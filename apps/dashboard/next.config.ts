import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
  output: "standalone",
  poweredByHeader: false,
  experimental: {
    // The TypeScript API is stable across the supported Node runtimes and avoids
    // a cross-spawn stdout issue observed with the CLI on this workstation.
    useTypeScriptCli: false,
  },
};

export default nextConfig;
