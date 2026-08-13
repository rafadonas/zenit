export interface MowingPostServiceException {
  exception_id: string;
  summary_id: string;
  mowing_order_id: string;
  road_code: string;
  segment_index: number;
  zone_type: "left" | "right" | "median" | "special";
  policy_version: string;
  creation_rationale: string;
  recommendation: "monitor" | "inspect_follow_up";
  applicable_threshold_cm: string | number;
  maximum_height_cm: string | number;
  threshold_exceeded: boolean;
  requires_human_review: true;
  phase: "post_service";
  data_status: "simulated";
  location_status: "not_collected";
  evidence_status: "simulated_reviewed_non_operational";
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  authorizes_field_work: false;
  created_at: string;
}

export interface MowingPostServiceExceptionCollection {
  items: MowingPostServiceException[];
  result_count: number;
  limit: number;
  truncated: boolean;
  warning: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDecimal(value: unknown): boolean {
  return (typeof value === "number" && Number.isFinite(value)) ||
    (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)));
}

function isException(value: unknown): value is MowingPostServiceException {
  if (!isRecord(value) || !isDecimal(value.applicable_threshold_cm) ||
    !isDecimal(value.maximum_height_cm)) return false;
  const threshold = Number(value.applicable_threshold_cm);
  const maximum = Number(value.maximum_height_cm);
  const exceeded = maximum > threshold;
  return [10, 30].includes(threshold) &&
    value.threshold_exceeded === exceeded &&
    value.recommendation === (exceeded ? "inspect_follow_up" : "monitor") &&
    typeof value.exception_id === "string" &&
    typeof value.summary_id === "string" &&
    typeof value.mowing_order_id === "string" &&
    typeof value.road_code === "string" &&
    Number.isInteger(value.segment_index) &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    typeof value.policy_version === "string" &&
    typeof value.creation_rationale === "string" &&
    value.requires_human_review === true &&
    value.phase === "post_service" &&
    value.data_status === "simulated" &&
    value.location_status === "not_collected" &&
    value.evidence_status === "simulated_reviewed_non_operational" &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false &&
    value.authorizes_field_work === false &&
    typeof value.created_at === "string" &&
    Number.isFinite(Date.parse(value.created_at));
}

export function isMowingPostServiceExceptionCollection(
  value: unknown,
): value is MowingPostServiceExceptionCollection {
  return isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isException) &&
    value.result_count === value.items.length &&
    typeof value.limit === "number" &&
    typeof value.truncated === "boolean" &&
    typeof value.warning === "string";
}
