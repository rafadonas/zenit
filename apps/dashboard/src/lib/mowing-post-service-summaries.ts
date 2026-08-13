export interface MowingPostServiceSummary {
  summary_id: string;
  mowing_order_id: string;
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
  phase: "post_service";
  summary_scope: "mowing_demo_post_service_only";
  location_status: "not_collected";
  data_status: "simulated";
  evidence_status: "simulated_reviewed_non_operational";
  eligible_for_field_evidence: false;
  eligible_for_field_execution: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  authorizes_field_work: false;
  generated_at: string;
}

export interface MowingPostServiceSummaryCollection {
  items: MowingPostServiceSummary[];
  result_count: number;
  limit: number;
  truncated: boolean;
  warning: "Resumo pós-serviço simulado; não comprova roçada, eficácia, conclusão ou operação oficial.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDecimal(value: unknown): value is string | number {
  return (typeof value === "number" && Number.isFinite(value)) ||
    (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value)));
}

function timestamp(value: unknown): boolean {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function isSummary(value: unknown): value is MowingPostServiceSummary {
  if (!isRecord(value)) return false;
  return typeof value.summary_id === "string" &&
    typeof value.mowing_order_id === "string" &&
    typeof value.summary_policy_version === "string" &&
    typeof value.generation_rationale === "string" &&
    value.measurement_count === 3 &&
    value.accepted_photo_review_count === 3 &&
    isDecimal(value.minimum_height_cm) &&
    isDecimal(value.maximum_height_cm) &&
    isDecimal(value.mean_height_cm) &&
    Number.isInteger(value.n1_count) &&
    Number.isInteger(value.n2_count) &&
    Number.isInteger(value.n3_count) &&
    value.phase === "post_service" &&
    value.summary_scope === "mowing_demo_post_service_only" &&
    value.location_status === "not_collected" &&
    value.data_status === "simulated" &&
    value.evidence_status === "simulated_reviewed_non_operational" &&
    value.eligible_for_field_evidence === false &&
    value.eligible_for_field_execution === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false &&
    value.authorizes_field_work === false &&
    timestamp(value.generated_at);
}

export function isMowingPostServiceSummaryCollection(
  value: unknown,
): value is MowingPostServiceSummaryCollection {
  if (!isRecord(value) || !Array.isArray(value.items)) return false;
  return value.warning ===
    "Resumo pós-serviço simulado; não comprova roçada, eficácia, conclusão ou operação oficial." &&
    Number.isInteger(value.result_count) &&
    Number.isInteger(value.limit) &&
    typeof value.truncated === "boolean" &&
    value.items.every(isSummary);
}
