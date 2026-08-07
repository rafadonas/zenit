import { describe, expect, it } from "vitest";

import { formatDistance, isSegmentCollection, projectSegments, type SegmentFeature } from "./segments";

const feature: SegmentFeature = {
  type: "Feature",
  geometry: {
    type: "LineString",
    coordinates: [
      [-46.8, -23.5],
      [-46.79, -23.49],
    ],
  },
  properties: {
    segment_id: "segment-1",
    segment_index: 1,
    start_distance_m: 100,
    end_distance_m: 200,
    data_status: "estimated",
    validation_status: "needs_validation",
    eligible_for_operations: false,
  },
};

describe("segment utilities", () => {
  it("validates the minimum GeoJSON contract", () => {
    expect(
      isSegmentCollection({ type: "FeatureCollection", features: [feature], metadata: {} }),
    ).toBe(true);
    expect(isSegmentCollection({ type: "FeatureCollection", features: [{}] })).toBe(false);
  });

  it("projects coordinates into a finite SVG path", () => {
    expect(projectSegments([feature])).toEqual([
      expect.objectContaining({ id: "segment-1", path: expect.stringMatching(/^M.+ L.+$/) }),
    ]);
  });

  it("formats operational distance in Portuguese", () => {
    expect(formatDistance(54.03)).toBe("54 m");
    expect(formatDistance(30854.03)).toBe("30,85 km");
  });
});
