import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dashboardSource = readFileSync(join(root, "components/corridor-dashboard.tsx"), "utf8");
const mapSource = readFileSync(join(root, "components/realistic-corridor-map.tsx"), "utf8");

describe("corridor dashboard map v2 contract", () => {
  it("keeps map selection available through search, filters, and an equivalent list", () => {
    expect(dashboardSource).toContain("parseCorridorSearchQuery");
    expect(dashboardSource).toContain("findSegmentIdByDistance");
    expect(dashboardSource).toContain("Classe histórica");
    expect(dashboardSource).toContain("Lista equivalente ao mapa");
    expect(dashboardSource).toContain("aria-current={selectedId === segment.segment_id");
  });

  it("labels historical vegetation classes as non-current and keeps tile failure usable", () => {
    expect(dashboardSource).toContain("referência histórica 28/03/2025");
    expect(dashboardSource).toContain("não representa condição atual");
    expect(mapSource).toContain("A lista equivalente, filtros e detalhes continuam disponíveis sem os tiles.");
  });

  it("keeps the raster base visible when the local database has no imported segments", () => {
    expect(dashboardSource).toContain("Mapa-base carregado sem segmentos");
    expect(dashboardSource).toContain("Nenhum dado foi presumido.");
    expect(dashboardSource).not.toContain('className="map-empty"');
  });
});
