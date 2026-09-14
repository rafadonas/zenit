import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../components/field-photo-queue.tsx"),
  "utf8",
);
const inspectionPage = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../app/photo-reviews/page.tsx"),
  "utf8",
);
const mowingPage = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../app/mowing-photo-reviews/page.tsx"),
  "utf8",
);

describe("field photo queue shared structure", () => {
  it("shares inspection and post-service queue navigation", () => {
    expect(source).toContain('aria-label="Filas de foto e campo"');
    expect(source).toContain("/photo-reviews");
    expect(source).toContain("/mowing-photo-reviews");
    expect(inspectionPage).toContain("<FieldQueueNavigation active=\"inspection\" />");
    expect(mowingPage).toContain("<FieldQueueNavigation active=\"mowing\" />");
  });

  it("keeps photo metadata readable when the image is unavailable", () => {
    expect(source).toContain("photo-unavailable-note");
    expect(source).toContain("use os metadados e o ID de evidência");
    expect(source).toContain("photoId.slice(0, 12)");
    expect(inspectionPage).toContain("FieldPhotoEvidence");
    expect(mowingPage).toContain("FieldPhotoEvidence");
  });
});
