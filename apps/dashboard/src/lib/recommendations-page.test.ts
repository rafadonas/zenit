import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../app/recommendations/page.tsx"),
  "utf8",
);

describe("recommendations page approval contract", () => {
  it("keeps the unified queue filterable without client state", () => {
    expect(source).toContain("filterRecommendationQueue");
    expect(source).toContain("filterHref");
    expect(source).toContain('aria-label="Filtros da fila de recomendações"');
    expect(source).toContain("Confiança baixa");
  });

  it("surfaces evidence and requires explicit non-authorization confirmation", () => {
    expect(source).toContain('className="evidence-panel"');
    expect(source).toContain("rule_version");
    expect(source).toContain("processor_version");
    expect(source).toContain('name="safety_confirmation"');
    expect(source).toContain("não autoriza roçada nem execução em campo");
  });
});
