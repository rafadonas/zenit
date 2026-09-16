import type { SegmentCollection } from "./segments";
import type { VegetationClass, VegetationMapCollection } from "./vegetation-map";

export const CORRIDOR_DEMO_QUERY = "gov-001";
export const CORRIDOR_DEMO_HREF = `/corridor?demo=${CORRIDOR_DEMO_QUERY}`;

export function corridorDemoEnabled(environment: Readonly<Record<string, string | undefined>>) {
  return ["development", "test", "demo"].includes(
    environment.DASHBOARD_APP_ENV ?? environment.NODE_ENV ?? "",
  );
}

const provenance = {
  source_id: "gov-001-visual-inventory-2026-09-14",
  source_code_sha256: "071e717dfb0ae6e1fee6f7d6aba1fe013c6e314f01b9839d7da0706cfb4ea262",
  is_simulated: true,
  eligible_for_operations: false,
  eligible_for_training: false,
  eligible_for_official_reporting: false,
};

// Preserve the original visual fixture coordinates, not a measured road axis.
export const demoSegments: SegmentCollection = {
  type: "FeatureCollection",
  features: Array.from({ length: 8 }, (_, index) => ({
    type: "Feature",
    geometry: {
      type: "LineString",
      coordinates: [
        [-46.82 + index * 0.01, -23.58 + index * 0.008],
        [-46.811 + index * 0.01, -23.572 + index * 0.008],
      ],
    },
    properties: {
      segment_id: `mock-segment-${index}`,
      segment_index: index,
      start_distance_m: index * 100,
      end_distance_m: (index + 1) * 100,
      data_status: "simulated",
      validation_status: "needs_validation",
      eligible_for_operations: false,
    },
  })),
  metadata: {
    ...provenance,
    road_code: "SP021",
    output_crs: "EPSG:4326",
    operational_warning: "Simulated GOV-001 visual fixture; distances are fictitious.",
  },
};

const classes: VegetationClass[] = ["N1", "N2", "N3", "unknown"];

export const demoVegetation: VegetationMapCollection = {
  type: "FeatureCollection",
  features: classes.map((vegetationClass, index) => {
    const x = -46.819 + index * 0.018;
    const y = -23.579 + index * 0.014;
    return {
      type: "Feature",
      geometry: {
        type: "MultiPolygon",
        coordinates: [[[[x, y], [x + 0.006, y], [x + 0.006, y + 0.004], [x, y + 0.004], [x, y]]]],
      },
      properties: {
        polygon_id: `mock-polygon-${index}`,
        source_index: index,
        road_code: "SP021",
        nearest_segment_id: `mock-segment-${index}`,
        segment_index: index,
        vegetation_class: vegetationClass,
        reference_date: "2025-03-28",
        version_label: "GOV-001 mock historical class",
        equipment_class: "visual-inventory-only",
        original_geometry_valid: true,
        // Legacy rendering contract; collection provenance marks the entire fixture simulated.
        data_status: "historical",
        mapping_status: "inferred_needs_validation",
        eligible_for_operations: false,
      },
    };
  }),
  metadata: {
    ...provenance,
    road_code: "SP021",
    reference_date: "2025-03-28",
    data_status: "historical",
    mapping_status: "inferred_needs_validation",
    warning: "Simulated classes and polygons, not imported historical evidence.",
  },
};
