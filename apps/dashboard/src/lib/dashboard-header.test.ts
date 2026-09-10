import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../components/dashboard-header.tsx"),
  "utf8",
);

describe("shared dashboard header", () => {
  it("keeps the product journey limited to five primary destinations", () => {
    expect(source.match(/area: "/g)).toHaveLength(5);
    expect(source).toContain('label: "Visão geral"');
    expect(source).toContain('label: "Mapa"');
    expect(source).toContain('label: "Decisões"');
    expect(source).toContain('label: "Campo"');
    expect(source).toContain('label: "Resultados"');
  });

  it("keeps logout protected by the server-provided CSRF token", () => {
    expect(source).toContain('action="/api/auth/logout"');
    expect(source).toContain('name="csrf_token"');
    expect(source).toContain("session.csrfToken");
  });
});
