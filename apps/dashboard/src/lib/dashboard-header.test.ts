import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardHeader } from "../components/dashboard-header";

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
    expect(source.match(/shortLabel: "/g)).toHaveLength(5);
  });

  it("keeps logout protected by the server-provided CSRF token", () => {
    expect(source).toContain('action="/api/auth/logout"');
    expect(source).toContain('name="csrf_token"');
    expect(source).toContain("session.csrfToken");
  });

  it("marks active route and renders page and role context", () => {
    const markup = renderToStaticMarkup(createElement(DashboardHeader, {
      active: "corridor",
      context: { label: "Rodovia", value: "SP021" },
      session: {
        csrfToken: "csrf-token",
        displayName: "Guilherme",
        roadRoles: [{ dataStatus: "prepared", roadCode: "SP021", role: "manager" }],
      },
    }));

    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain('data-compact-label="Mapa"');
    expect(markup).toContain('aria-label="Contexto da página"');
    expect(markup).toContain("Gestor · SP021");
    expect(markup).toContain('data-status="prepared"');
  });
});
