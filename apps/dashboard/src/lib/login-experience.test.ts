import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const sourceRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const formSource = readFileSync(join(sourceRoot, "components/login-form.tsx"), "utf8");
const pageSource = readFileSync(join(sourceRoot, "app/login/page.tsx"), "utf8");

describe("dashboard login experience", () => {
  it("supports keyboard submission and announces one in-progress request", () => {
    expect(formSource).toContain('type="submit"');
    expect(formSource).toContain("onSubmit={handleSubmit}");
    expect(formSource).toContain("disabled={submitting}");
    expect(formSource).toContain('aria-live="polite"');
    expect(formSource).toContain('aria-busy={submitting}');
  });

  it("keeps the access token outside client-visible login code", () => {
    const loginSources = `${formSource}\n${pageSource}`;
    expect(loginSources).not.toContain("localStorage");
    expect(loginSources).not.toContain("sessionStorage");
    expect(loginSources).not.toContain("access_token");
  });

  it("labels environment and profile context before entry", () => {
    expect(pageSource).toContain('aria-label="Contexto de acesso"');
    expect(pageSource).toContain("Demonstração local");
    expect(pageSource).toContain("Confirmado após a entrada");
  });
});
