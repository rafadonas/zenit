export type VegetationClass = "N1" | "N2" | "N3" | "X" | "unknown";

export interface VegetationMapFeature {
  type: "Feature";
  geometry: {
    type: "MultiPolygon";
    coordinates: number[][][][];
  };
  properties: {
    polygon_id: string;
    source_index: number;
    road_code: string;
    nearest_segment_id: string;
    segment_index: number;
    vegetation_class: VegetationClass;
    reference_date: string;
    version_label: string;
    equipment_class: string;
    original_geometry_valid: boolean;
    data_status: "historical";
    mapping_status: "inferred_needs_validation";
    eligible_for_operations: false;
  };
}

export interface VegetationMapCollection {
  type: "FeatureCollection";
  features: VegetationMapFeature[];
  metadata: {
    road_code?: string;
    reference_date: string;
    data_status: "historical";
    mapping_status: "inferred_needs_validation";
    classification_rule?: string;
    warning?: string;
    [key: string]: unknown;
  };
}

function isPosition(value: unknown): value is number[] {
  return Array.isArray(value) && value.length >= 2 &&
    value.every((coordinate) => typeof coordinate === "number" && Number.isFinite(coordinate));
}

function isFeature(value: unknown): value is VegetationMapFeature {
  if (!value || typeof value !== "object") return false;
  const feature = value as Partial<VegetationMapFeature>;
  const properties = feature.properties;
  return feature.type === "Feature" &&
    feature.geometry?.type === "MultiPolygon" &&
    Array.isArray(feature.geometry.coordinates) &&
    feature.geometry.coordinates.every((polygon) =>
      Array.isArray(polygon) && polygon.every((ring) =>
        Array.isArray(ring) && ring.every(isPosition))) &&
    typeof properties?.polygon_id === "string" &&
    typeof properties.nearest_segment_id === "string" &&
    typeof properties.segment_index === "number" &&
    ["N1", "N2", "N3", "X", "unknown"].includes(String(properties.vegetation_class)) &&
    properties.data_status === "historical" &&
    properties.mapping_status === "inferred_needs_validation" &&
    properties.eligible_for_operations === false;
}

export function isVegetationMapCollection(value: unknown): value is VegetationMapCollection {
  if (!value || typeof value !== "object") return false;
  const collection = value as Partial<VegetationMapCollection>;
  return collection.type === "FeatureCollection" &&
    Array.isArray(collection.features) &&
    collection.features.every(isFeature) &&
    collection.metadata?.data_status === "historical" &&
    collection.metadata.mapping_status === "inferred_needs_validation" &&
    typeof collection.metadata.reference_date === "string";
}

export function vegetationClassLabel(value: VegetationClass): string {
  if (value === "N1") return "N1 · abaixo de 10 cm";
  if (value === "N2") return "N2 · entre 10 e 30 cm";
  if (value === "N3") return "N3 · acima de 30 cm";
  if (value === "X") return "Não aplicável";
  return "Sem classificação";
}
