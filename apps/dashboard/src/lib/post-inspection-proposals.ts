export interface PreparedPostInspectionProposal {
  proposal_id: string;
  summary_id: string;
  work_order_id: string;
  road_code: string;
  segment_index: number;
  zone_type: "left" | "right" | "median" | "special";
  policy_version: string;
  creation_rationale: string;
  recommendation: "monitor" | "mowing_review";
  applicable_threshold_cm: string | number;
  maximum_height_cm: string | number;
  threshold_exceeded: boolean;
  requires_human_review: true;
  location_status: "simulated";
  evidence_status: "prepared_reviewed_non_operational";
  data_status: "prepared";
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  authorizes_field_work: false;
  created_at: string;
  review_count: number;
  latest_review_id: string | null;
  latest_review_decision: "accepted" | "rejected" | "adjusted" | null;
  latest_adjusted_recommendation: "monitor" | "mowing_review" | null;
  latest_review_rationale: string | null;
  latest_reviewed_at: string | null;
  review_state: "awaiting_review" | "review_recorded_no_work_authorization";
}

export interface PreparedProposalCollection {
  items: PreparedPostInspectionProposal[];
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

function isProposal(value: unknown): value is PreparedPostInspectionProposal {
  if (!isRecord(value) || !isDecimal(value.applicable_threshold_cm) ||
    !isDecimal(value.maximum_height_cm)) return false;
  const threshold = Number(value.applicable_threshold_cm);
  const maximum = Number(value.maximum_height_cm);
  const exceeded = maximum > threshold;
  const unreviewed = value.review_count === 0;
  const reviewConsistent = unreviewed
    ? value.latest_review_id === null && value.latest_review_decision === null &&
      value.latest_adjusted_recommendation === null && value.latest_review_rationale === null &&
      value.latest_reviewed_at === null && value.review_state === "awaiting_review"
    : typeof value.review_count === "number" && value.review_count > 0 &&
      typeof value.latest_review_id === "string" &&
      ["accepted", "rejected", "adjusted"].includes(String(value.latest_review_decision)) &&
      typeof value.latest_reviewed_at === "string" &&
      value.review_state === "review_recorded_no_work_authorization" &&
      ((value.latest_review_decision === "adjusted") ===
        ["monitor", "mowing_review"].includes(String(value.latest_adjusted_recommendation)));
  return [10, 30].includes(threshold) && value.threshold_exceeded === exceeded &&
    typeof value.review_count === "number" && Number.isInteger(value.review_count) &&
    reviewConsistent &&
    value.recommendation === (exceeded ? "mowing_review" : "monitor") &&
    typeof value.proposal_id === "string" &&
    typeof value.summary_id === "string" && typeof value.work_order_id === "string" &&
    typeof value.road_code === "string" && typeof value.segment_index === "number" &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    typeof value.policy_version === "string" && typeof value.creation_rationale === "string" &&
    typeof value.threshold_exceeded === "boolean" && value.requires_human_review === true &&
    value.location_status === "simulated" &&
    value.evidence_status === "prepared_reviewed_non_operational" &&
    value.data_status === "prepared" && value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false && value.authorizes_field_work === false &&
    typeof value.created_at === "string";
}

export function isPreparedProposalCollection(value: unknown): value is PreparedProposalCollection {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(isProposal) &&
    value.result_count === value.items.length && typeof value.limit === "number" &&
    typeof value.truncated === "boolean" && typeof value.warning === "string";
}
