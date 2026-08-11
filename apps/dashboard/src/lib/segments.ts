export type Position = [number, number];

export interface SegmentProperties {
  segment_id: string;
  segment_index: number;
  start_distance_m: number;
  end_distance_m: number;
  data_status: "estimated" | "real" | "simulated" | "prepared" | "inconclusive";
  validation_status: "needs_validation" | "validated" | "rejected";
  eligible_for_operations: boolean;
}

export interface SegmentFeature {
  type: "Feature";
  geometry: {
    type: "LineString";
    coordinates: Position[];
  };
  properties: SegmentProperties;
}

export interface SegmentCollection {
  type: "FeatureCollection";
  features: SegmentFeature[];
  metadata: {
    road_code?: string;
    metric_crs?: string;
    output_crs?: string;
    operational_warning?: string;
    [key: string]: unknown;
  };
}

export interface ProjectedSegment {
  id: string;
  path: string;
  properties: SegmentProperties;
}

export interface ProjectedPosition {
  x: number;
  y: number;
}

export type MapProjection = (position: Position) => ProjectedPosition;

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 680;
const MAP_PADDING = 54;

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isSegmentCollection(value: unknown): value is SegmentCollection {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SegmentCollection>;
  return (
    candidate.type === "FeatureCollection" &&
    Array.isArray(candidate.features) &&
    candidate.features.every(
      (feature) =>
        feature?.type === "Feature" &&
        feature.geometry?.type === "LineString" &&
        Array.isArray(feature.geometry.coordinates) &&
        feature.geometry.coordinates.every(
          (position) =>
            Array.isArray(position) &&
            position.length >= 2 &&
            isNumber(position[0]) &&
            isNumber(position[1]),
        ) &&
        typeof feature.properties?.segment_id === "string" &&
        isNumber(feature.properties?.segment_index),
    )
  );
}

export function createMapProjection(features: SegmentFeature[]): MapProjection | null {
  const positions = features.flatMap((feature) => feature.geometry.coordinates);
  if (positions.length === 0) return null;

  const longitudes = positions.map(([longitude]) => longitude);
  const latitudes = positions.map(([, latitude]) => latitude);
  const minLongitude = Math.min(...longitudes);
  const maxLongitude = Math.max(...longitudes);
  const minLatitude = Math.min(...latitudes);
  const maxLatitude = Math.max(...latitudes);
  const longitudeSpan = Math.max(maxLongitude - minLongitude, Number.EPSILON);
  const latitudeSpan = Math.max(maxLatitude - minLatitude, Number.EPSILON);
  const availableWidth = MAP_WIDTH - MAP_PADDING * 2;
  const availableHeight = MAP_HEIGHT - MAP_PADDING * 2;
  const scale = Math.min(availableWidth / longitudeSpan, availableHeight / latitudeSpan);
  const drawnWidth = longitudeSpan * scale;
  const drawnHeight = latitudeSpan * scale;
  const offsetX = (MAP_WIDTH - drawnWidth) / 2;
  const offsetY = (MAP_HEIGHT - drawnHeight) / 2;

  return ([longitude, latitude]: Position) => ({
    x: offsetX + (longitude - minLongitude) * scale,
    y: MAP_HEIGHT - (offsetY + (latitude - minLatitude) * scale),
  });
}

export function projectSegments(features: SegmentFeature[]): ProjectedSegment[] {
  const project = createMapProjection(features);
  if (project === null) return [];
  return features.map((feature) => {
    const commands = feature.geometry.coordinates.map(([longitude, latitude], index) => {
      const { x, y } = project([longitude, latitude]);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    });
    return {
      id: feature.properties.segment_id,
      path: commands.join(" "),
      properties: feature.properties,
    };
  });
}

export function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} km`;
  }
  return `${meters.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} m`;
}

export function findSegmentIdByIndex(
  features: SegmentFeature[],
  segmentIndex: number,
): string | null {
  if (!Number.isInteger(segmentIndex) || segmentIndex < 0) return null;
  return (
    features.find((feature) => feature.properties.segment_index === segmentIndex)?.properties
      .segment_id ?? null
  );
}
