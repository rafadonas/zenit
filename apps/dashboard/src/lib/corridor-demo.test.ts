import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "../app/page";
import {
  CORRIDOR_DEMO_QUERY,
  corridorDemoEnabled,
  demoSegments,
  demoVegetation,
} from "./corridor-demo";
import { isSegmentCollection } from "./segments";
import { isVegetationMapCollection } from "./vegetation-map";

vi.mock("../components/realistic-corridor-map", () => ({ RealisticCorridorMap: () => null }));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("recovered GOV-001 corridor", () => {
  it("preserves eight visual segments and four mock polygons in the rendering contracts", () => {
    expect(isSegmentCollection(demoSegments)).toBe(true);
    expect(isVegetationMapCollection(demoVegetation)).toBe(true);
    expect(demoSegments.features).toHaveLength(8);
    expect(demoVegetation.features).toHaveLength(4);
    expect(demoSegments.features[0].geometry.coordinates).toEqual([
      [-46.82, -23.58], [-46.811, -23.572],
    ]);
    expect(demoVegetation.features.map((feature) => feature.properties.vegetation_class))
      .toEqual(["N1", "N2", "N3", "unknown"]);
    for (const feature of demoVegetation.features) {
      expect(demoSegments.features.some((segment) =>
        segment.properties.segment_id === feature.properties.nearest_segment_id)).toBe(true);
    }
  });

  it("keeps recovered data simulated, traceable and ineligible", () => {
    for (const collection of [demoSegments, demoVegetation]) {
      expect(collection.metadata).toMatchObject({
        is_simulated: true,
        eligible_for_operations: false,
        eligible_for_training: false,
        eligible_for_official_reporting: false,
      });
      expect(collection.metadata.source_code_sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(collection.features.every((feature) => !feature.properties.eligible_for_operations)).toBe(true);
    }
    expect(demoSegments.features.every((feature) => feature.properties.data_status === "simulated"))
      .toBe(true);
  });

  it("is unavailable in staging, production, and unspecified environments", () => {
    for (const environment of [{}, { NODE_ENV: "production" },
      { DASHBOARD_APP_ENV: "staging", NODE_ENV: "development" },
      { DASHBOARD_APP_ENV: "production" }]) {
      expect(corridorDemoEnabled(environment)).toBe(false);
    }
    expect(corridorDemoEnabled({ DASHBOARD_APP_ENV: "development", NODE_ENV: "production" }))
      .toBe(true);
  });

  it("renders an explicitly selected demo without requesting the API or claiming a raw source", async () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "development");
    const fetchMock = vi.fn().mockRejectedValue(new Error("API offline"));
    vi.stubGlobal("fetch", fetchMock);
    const page = await Home({ searchParams: Promise.resolve({ demo: CORRIDOR_DEMO_QUERY, segment: "3" }) });
    const markup = renderToStaticMarkup(page);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(markup).toContain("Mapa demonstrativo");
    expect(markup).toContain("Simulado");
    expect(markup).toContain("fictícias");
    expect(markup).toContain("polígonos fictícios GOV-001");
    expect(markup).not.toContain("polígonos do KMZ fornecido");
    expect(markup).not.toContain("30,85 km");
    expect(markup).not.toContain("Consultando evidências satelitais");
  });

  it.each([undefined, "unknown", [CORRIDOR_DEMO_QUERY]])(
    "does not replace an API failure with demo data for query %s",
    async (demo) => {
      vi.stubEnv("DASHBOARD_APP_ENV", "development");
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("API offline")));
      await expect(Home({ searchParams: Promise.resolve({ demo }) })).rejects.toThrow("API offline");
    },
  );

  it("ignores the demo query in production and still requests real API data", async () => {
    vi.stubEnv("DASHBOARD_APP_ENV", "production");
    const fetchMock = vi.fn().mockRejectedValue(new Error("API offline"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(Home({ searchParams: Promise.resolve({ demo: CORRIDOR_DEMO_QUERY }) }))
      .rejects.toThrow("API offline");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
