import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../app/mowing-post-service-summaries/page.tsx"),
  "utf8",
);

describe("mowing post-service results page contract", () => {
  it("keeps before and after sources visibly separated", () => {
    expect(source).toContain("buildMowingPostServiceResultHistory");
    expect(source).toContain('aria-label="Histórico e comparação"');
    expect(source).toContain("Fonte: contrato não disponível");
    expect(source).toContain("Fonte: resumo pós-serviço simulado");
  });

  it("keeps export copy tied to status and provenance", () => {
    expect(source).toContain("status/proveniência");
    expect(source).toContain("relatório oficial");
    expect(source).toContain("autorização de campo");
  });
});
