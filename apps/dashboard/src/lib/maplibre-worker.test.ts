import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const dashboardRoot = fileURLToPath(new URL("../../", import.meta.url));
const maplibreRoot = dirname(createRequire(import.meta.url).resolve("maplibre-gl/package.json"));

describe("MapLibre worker packaging", () => {
  it("copies the matching worker and its relative shared import without bundler transformations", () => {
    execFileSync(process.execPath, [join(dashboardRoot, "scripts/copy-maplibre-worker.mjs")]);
    for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
      expect(readFileSync(join(dashboardRoot, "public/maplibre", file)))
        .toEqual(readFileSync(join(maplibreRoot, "dist", file)));
    }
    expect(readFileSync(join(dashboardRoot, "public/maplibre/LICENSE.txt")))
      .toEqual(readFileSync(join(maplibreRoot, "LICENSE.txt")));
  });
});
