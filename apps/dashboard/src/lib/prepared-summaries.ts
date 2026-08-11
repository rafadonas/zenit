export interface PreparedInspectionSummary {
  summary_id: string;
  work_order_id: string;
  summary_policy_version: string;
  generation_rationale: string;
  measurement_count: 3;
  accepted_photo_review_count: 3;
  minimum_height_cm: string | number;
  maximum_height_cm: string | number;
  mean_height_cm: string | number;
  n1_count: number;
  n2_count: number;
  n3_count: number;
  class_rule: "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm";
  location_status: "simulated";
  evidence_status: "prepared_reviewed_non_operational";
  data_status: "prepared";
  eligible_for_field_evidence: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  authorizes_field_work: false;
  generated_at: string;
}

export interface PreparedSummaryCollection {
  items: PreparedInspectionSummary[];
  result_count: number;
  limit: number;
  truncated: boolean;
  warning: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDecimal(value: unknown): value is string | number {
  return (typeof value === "number" && Number.isFinite(value)) ||
    (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)));
}

function isSummary(value: unknown): value is PreparedInspectionSummary {
  return isRecord(value) &&
    typeof value.summary_id === "string" && typeof value.work_order_id === "string" &&
    typeof value.summary_policy_version === "string" &&
    typeof value.generation_rationale === "string" && value.measurement_count === 3 &&
    value.accepted_photo_review_count === 3 && isDecimal(value.minimum_height_cm) &&
    isDecimal(value.maximum_height_cm) && isDecimal(value.mean_height_cm) &&
    typeof value.n1_count === "number" && Number.isInteger(value.n1_count) &&
    typeof value.n2_count === "number" && Number.isInteger(value.n2_count) &&
    typeof value.n3_count === "number" && Number.isInteger(value.n3_count) &&
    value.n1_count + value.n2_count + value.n3_count === 3 &&
    value.class_rule === "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm" &&
    value.location_status === "simulated" &&
    value.evidence_status === "prepared_reviewed_non_operational" &&
    value.data_status === "prepared" && value.eligible_for_field_evidence === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false && value.authorizes_field_work === false &&
    typeof value.generated_at === "string";
}

export function isPreparedSummaryCollection(value: unknown): value is PreparedSummaryCollection {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(isSummary) &&
    typeof value.result_count === "number" && value.result_count === value.items.length &&
    typeof value.limit === "number" && typeof value.truncated === "boolean" &&
    typeof value.warning === "string";
}
