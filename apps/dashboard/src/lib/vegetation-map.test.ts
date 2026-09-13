import { describe, expect, it } from "vitest";

import { isVegetationMapCollection, vegetationClassLabel } from "./vegetation-map";

const collection = {
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    geometry: {
      type: "MultiPolygon",
      coordinates: [[[[-46.83, -23.63], [-46.82, -23.63], [-46.83, -23.63]]]],
    },
    properties: {
      polygon_id: "polygon-1",
      source_index: 1,
      road_code: "SP021",
      nearest_segment_id: "segment-1",
      segment_index: 0,
      vegetation_class: "N3",
      reference_date: "2025-03-28",
      version_label: "reference-v2",
      equipment_class: "manual",
      original_geometry_valid: true,
      data_status: "historical",
      mapping_status: "inferred_needs_validation",
      eligible_for_operations: false,
    },
  }],
  metadata: {
    reference_date: "2025-03-28",
    data_status: "historical",
    mapping_status: "inferred_needs_validation",
  },
};

describe("vegetation map contract", () => {
  it("accepts historical, non-operational polygons", () => {
    expect(isVegetationMapCollection(collection)).toBe(true);
  });

  it("fails closed on operational claims", () => {
    const unsafe = structuredClone(collection);
    unsafe.features[0].properties.eligible_for_operations = true;
    expect(isVegetationMapCollection(unsafe)).toBe(false);
  });

  it("presents the preserved historical classes", () => {
    expect(vegetationClassLabel("N1")).toContain("abaixo de 10 cm");
    expect(vegetationClassLabel("N3")).toContain("acima de 30 cm");
  });
});
