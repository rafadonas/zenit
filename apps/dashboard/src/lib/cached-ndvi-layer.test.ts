import { describe, expect, it } from "vitest";

import {
  CACHED_NDVI_ASSET_SHA256,
  cachedNdviCells,
  ndviCellColor,
  observationSupportsCachedNdviLayer,
} from "./cached-ndvi-layer";
import type { SatelliteObservation } from "./satellite-observations";

const observation: SatelliteObservation = {
  analysis_run_id: "run-1",
  scene_id: "scene-1",
  provider: "copernicus_sentinel_hub",
  collection: "sentinel-2-l2a",
  sensor: "sentinel-2",
  acquired_at: "2026-07-29T13:18:42.502Z",
  cache_status: "partially_cached",
  scene_data_status: "real",
  zone_type: "left",
  zone_data_status: "prepared",
  mean_ndvi: 0.097354,
  valid_pixel_percent: 100,
  conclusion: "inconclusive",
  recommendation: "inspect",
  confidence_band: "low",
  requires_human_approval: true,
  eligible_for_official_reporting: false,
  rule_version: "rule-v1",
  processor_version: "processor-v1",
  explanation: {},
  assets: [
    {
      role: "ndvi_aoi_crop_685d33f38e064428",
      media_type: "image/tiff",
      checksum_sha256: CACHED_NDVI_ASSET_SHA256,
    },
  ],
};

describe("checksum-bound cached NDVI layer", () => {
  it("exposes the exact 5 by 11 georeferenced grid", () => {
    const cells = cachedNdviCells();

    expect(cells).toHaveLength(55);
    expect(cells.filter((cell) => cell.value !== null)).toHaveLength(35);
    expect(cells[0]).toMatchObject({ column: 0, row: 0, value: null });
    expect(cells[54]).toMatchObject({ column: 4, row: 10, value: null });
    expect(cells[0].northWest[0]).toBeLessThan(cells[0].southEast[0]);
    expect(cells[0].northWest[1]).toBeGreaterThan(cells[0].southEast[1]);
  });

  it("enables the layer only for the exact safe persisted observation", () => {
    expect(observationSupportsCachedNdviLayer(observation)).toBe(true);
    expect(
      observationSupportsCachedNdviLayer({
        ...observation,
        assets: [{ ...observation.assets[0], checksum_sha256: "a".repeat(64) }],
      }),
    ).toBe(false);
    expect(
      observationSupportsCachedNdviLayer({
        ...observation,
        eligible_for_official_reporting: true,
      }),
    ).toBe(false);
  });

  it("uses descriptive NDVI colors without creating height classes", () => {
    expect(ndviCellColor(null)).toBe("#3f4654");
    expect(ndviCellColor(-0.1)).toBe("#5d86c2");
    expect(ndviCellColor(0.05)).toBe("#d9c98a");
    expect(ndviCellColor(0.15)).toBe("#a8c96a");
    expect(ndviCellColor(0.25)).toBe("#4d9b50");
  });
});
