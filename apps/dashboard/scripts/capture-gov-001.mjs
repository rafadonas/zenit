#!/usr/bin/env node

import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync, spawnSync } from "node:child_process";

const repoRoot = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const outputDirectory = resolve(
  process.env.GOV_001_OUTPUT_DIRECTORY ??
    join(repoRoot, "data/processed/gov-001/web"),
);
const chromeBinary =
  process.env.CHROME_BINARY ?? "/opt/google/chrome/chrome";
const unauthenticatedBaseUrl = new URL(
  process.env.GOV_001_UNAUTHENTICATED_BASE_URL ?? "http://127.0.0.1:3100",
);
const authenticatedBootstrapBaseUrl = new URL(
  process.env.GOV_001_AUTHENTICATED_BOOTSTRAP_BASE_URL ??
    "http://127.0.0.1:3000",
);
const authenticatedCaptureBaseUrl = new URL(
  process.env.GOV_001_AUTHENTICATED_CAPTURE_BASE_URL ??
    unauthenticatedBaseUrl.href,
);

const widths = [360, 768, 1024, 1440];
const authenticatedRoutes = [
  "overview",
  "corridor",
  "recommendations",
  "photo-reviews",
  "mowing-photo-reviews",
  "mowing-post-service-summaries",
];
const allowedHosts = new Set(["127.0.0.1", "localhost", "::1"]);

for (const url of [
  unauthenticatedBaseUrl,
  authenticatedBootstrapBaseUrl,
  authenticatedCaptureBaseUrl,
]) {
  if (url.protocol !== "http:" || !allowedHosts.has(url.hostname)) {
    throw new Error(`GOV-001 captures only accept loopback HTTP URLs: ${url}`);
  }
}
if (!existsSync(chromeBinary)) {
  throw new Error(`Chrome binary not found: ${chromeBinary}`);
}

mkdirSync(outputDirectory, { recursive: true });
const captures = [];

function chromeArguments(
  profileDirectory,
  width,
  url,
  screenshotPath,
  virtualTimeBudget = 5000,
) {
  const args = [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--hide-scrollbars",
    `--user-data-dir=${profileDirectory}`,
    `--window-size=${width},900`,
  ];
  if (virtualTimeBudget > 0) {
    args.push(`--virtual-time-budget=${virtualTimeBudget}`);
  }
  if (screenshotPath) args.push(`--screenshot=${screenshotPath}`);
  args.push(url.href);
  return args;
}

function runChrome(
  profileDirectory,
  width,
  url,
  screenshotPath,
  virtualTimeBudget,
) {
  const result = spawnSync(
    chromeBinary,
    chromeArguments(
      profileDirectory,
      width,
      url,
      screenshotPath,
      virtualTimeBudget,
    ),
    { encoding: "utf8" },
  );
  if (result.status !== 0) {
    throw new Error(
      `Chrome failed for ${url}: ${result.stderr || result.stdout}`,
    );
  }
}

function recordCapture(file, route, state, width) {
  const bytes = readFileSync(join(outputDirectory, file));
  if (bytes.toString("ascii", 1, 4) !== "PNG") {
    throw new Error(`${file} is not a PNG capture`);
  }
  captures.push({
    file,
    route,
    state,
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    requested_width: width,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    bytes: bytes.length,
  });
}

function capture(
  profileDirectory,
  width,
  route,
  state,
  url,
  virtualTimeBudget,
) {
  const file = `${route}-${state}-${width}.png`;
  runChrome(
    profileDirectory,
    width,
    url,
    join(outputDirectory, file),
    virtualTimeBudget,
  );
  recordCapture(file, `/${route}`, state, width);
}

for (const width of widths) {
  const profileDirectory = mkdtempSync(join(tmpdir(), "zenit-gov-001-"));
  try {
    capture(
      profileDirectory,
      width,
      "login",
      "idle",
      new URL("/login", unauthenticatedBaseUrl),
    );
    capture(
      profileDirectory,
      width,
      "login",
      "error",
      new URL("/login?error=service-unavailable", unauthenticatedBaseUrl),
    );

    // The bootstrap is a local fixture identity. Its cookie name must match the
    // capture server, but no cookie value is read or written to the manifest.
    // At 360 px its immediate redirect also records the global loading screen.
    if (width === 360) {
      capture(
        profileDirectory,
        width,
        "overview",
        "loading",
        new URL("/overview", authenticatedBootstrapBaseUrl),
        0,
      );
    } else {
      runChrome(
        profileDirectory,
        width,
        new URL("/overview", authenticatedBootstrapBaseUrl),
      );
    }
    for (const route of authenticatedRoutes) {
      capture(
        profileDirectory,
        width,
        route,
        "success",
        new URL(`/${route}`, authenticatedCaptureBaseUrl),
      );
    }
  } finally {
    rmSync(profileDirectory, { force: true, recursive: true });
  }
}

const sourcePaths = [
  "apps/dashboard/src/app/loading.tsx",
  "apps/dashboard/src/app/error.tsx",
  "apps/dashboard/src/app/login/page.tsx",
  "apps/dashboard/src/app/overview/page.tsx",
  "apps/dashboard/src/app/corridor/page.tsx",
  "apps/dashboard/src/app/recommendations/page.tsx",
  "apps/dashboard/src/app/photo-reviews/page.tsx",
  "apps/dashboard/src/app/mowing-photo-reviews/page.tsx",
  "apps/dashboard/src/app/mowing-post-service-summaries/page.tsx",
  "apps/dashboard/scripts/capture-gov-001.mjs",
];
const sources = sourcePaths.map((path) => {
  const bytes = readFileSync(join(repoRoot, path));
  return {
    path,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
});

const manifest = {
  ticket: "GOV-001",
  captured_at_utc: new Date().toISOString(),
  assessed_revision: execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: repoRoot,
    encoding: "utf8",
  }).trim(),
  evidence_type: "headless Chrome viewport screenshots",
  data_status: "prepared fixture",
  eligible_for_field_execution: false,
  eligible_for_model_training: false,
  eligible_for_official_reporting: false,
  viewport_height: 900,
  states: {
    loading: "captured at 360 px and source-audited in apps/dashboard/src/app/loading.tsx",
    empty: "rendered in authenticated empty queue captures",
    error: "rendered in login-error captures and source-audited error boundary",
    success: "rendered for every authenticated route",
  },
  limitations: [
    "Viewport captures are not full-page exports.",
    "Headless Chrome does not replace keyboard or screen-reader verification.",
    "Manager identity and queue contents are local prepared fixtures.",
    "Map geometry and tiles are not authoritative operational evidence.",
  ],
  sources,
  captures,
};
writeFileSync(
  join(outputDirectory, "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
);

console.log(
  `Captured ${captures.length} GOV-001 web views in ${outputDirectory}`,
);
