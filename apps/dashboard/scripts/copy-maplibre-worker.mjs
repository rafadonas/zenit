import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = dirname(createRequire(import.meta.url).resolve("maplibre-gl/package.json"));
const destination = fileURLToPath(new URL("../public/maplibre/", import.meta.url));

mkdirSync(destination, { recursive: true });
// The module worker imports its shared sibling; Next must serve both unchanged.
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(join(packageRoot, "dist", file), join(destination, file));
}
copyFileSync(join(packageRoot, "LICENSE.txt"), join(destination, "LICENSE.txt"));
