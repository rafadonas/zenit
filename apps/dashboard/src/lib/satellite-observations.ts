export interface SatelliteAssetEvidence {
  role: string;
  media_type: string;
  checksum_sha256: string;
}

export interface SatelliteObservation {
  analysis_run_id: string;
  scene_id: string;
  provider: string;
  collection: string;
  sensor: "sentinel-2" | "cbers-4a";
  acquired_at: string;
  cache_status: "discovered" | "partially_cached" | "cached";
  scene_data_status: string;
  zone_type: "left" | "right" | "median" | "special";
  zone_data_status: string;
  mean_ndvi: number | null;
  valid_pixel_percent: number;
  conclusion: "conclusive" | "inconclusive";
  recommendation: "monitor" | "inspect" | "mowing_review";
  confidence_band: "low" | "medium" | "high";
  requires_human_approval: boolean;
  eligible_for_official_reporting: boolean;
  rule_version: string;
  processor_version: string;
  explanation: Record<string, unknown>;
  assets: SatelliteAssetEvidence[];
}

export interface SatelliteObservationCollection {
  items: SatelliteObservation[];
  metadata: {
    segment_id: string;
    result_count: number;
    warning?: string;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isAsset(value: unknown): value is SatelliteAssetEvidence {
  if (!isRecord(value)) return false;
  return (
    typeof value.role === "string" &&
    typeof value.media_type === "string" &&
    typeof value.checksum_sha256 === "string" &&
    /^[a-f0-9]{64}$/i.test(value.checksum_sha256)
  );
}

function isObservation(value: unknown): value is SatelliteObservation {
  if (!isRecord(value)) return false;
  return (
    typeof value.analysis_run_id === "string" &&
    typeof value.scene_id === "string" &&
    typeof value.provider === "string" &&
    typeof value.collection === "string" &&
    (value.sensor === "sentinel-2" || value.sensor === "cbers-4a") &&
    typeof value.acquired_at === "string" &&
    typeof value.scene_data_status === "string" &&
    typeof value.zone_data_status === "string" &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    (value.mean_ndvi === null || isNumber(value.mean_ndvi)) &&
    isNumber(value.valid_pixel_percent) &&
    (value.conclusion === "conclusive" || value.conclusion === "inconclusive") &&
    ["monitor", "inspect", "mowing_review"].includes(String(value.recommendation)) &&
    ["low", "medium", "high"].includes(String(value.confidence_band)) &&
    typeof value.requires_human_approval === "boolean" &&
    typeof value.eligible_for_official_reporting === "boolean" &&
    typeof value.rule_version === "string" &&
    typeof value.processor_version === "string" &&
    isRecord(value.explanation) &&
    Array.isArray(value.assets) &&
    value.assets.every(isAsset)
  );
}

export function isSatelliteObservationCollection(
  value: unknown,
): value is SatelliteObservationCollection {
  if (!isRecord(value) || !Array.isArray(value.items) || !isRecord(value.metadata)) {
    return false;
  }
  return (
    value.items.every(isObservation) &&
    typeof value.metadata.segment_id === "string" &&
    isNumber(value.metadata.result_count)
  );
}

export function formatAcquisitionDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data inválida";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(date);
}
