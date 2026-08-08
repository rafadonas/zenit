import { describe, expect, it } from "vitest";

import {
  formatAcquisitionDate,
  isSatelliteObservationCollection,
} from "./satellite-observations";

const observation = {
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
  explanation: { input_data_status: "prepared" },
  assets: [{ role: "ndvi", media_type: "image/tiff", checksum_sha256: "a".repeat(64) }],
};

describe("satellite observation utilities", () => {
  it("accepts a provenance-safe observation contract", () => {
    expect(
      isSatelliteObservationCollection({
        items: [observation],
        metadata: {
          segment_id: "segment-1",
          result_count: 1,
          total_count: 12,
          limit: 10,
          truncated: true,
        },
      }),
    ).toBe(true);
  });

  it("rejects evidence without a valid checksum", () => {
    expect(
      isSatelliteObservationCollection({
        items: [{ ...observation, assets: [{ ...observation.assets[0], checksum_sha256: "bad" }] }],
        metadata: {
          segment_id: "segment-1",
          result_count: 1,
          total_count: 1,
          limit: 10,
          truncated: false,
        },
      }),
    ).toBe(false);
  });

  it("formats the acquisition date without presenting it as current", () => {
    expect(formatAcquisitionDate(observation.acquired_at)).toBe("29/07/2026");
  });
});
