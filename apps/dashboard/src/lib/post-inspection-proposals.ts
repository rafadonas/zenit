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
  prepared_mowing_order_id: string | null;
  mowing_order_state: "not_prepared" | "prepared_no_execution_authorization";
  resource_plan_count: number;
  latest_resource_plan_id: string | null;
  latest_team_reference: string | null;
  latest_equipment_reference: string | null;
  latest_resource_plan_rationale: string | null;
  latest_resource_plan_created_at: string | null;
  readiness_assessment_count: number;
  latest_readiness_assessment_id: string | null;
  latest_readiness_resource_plan_id: string | null;
  latest_weather_result: "clear" | "blocked" | "inconclusive" | null;
  latest_weather_source_reference: string | null;
  latest_safety_result: "clear" | "blocked" | "inconclusive" | null;
  latest_safety_source_reference: string | null;
  latest_readiness_rationale: string | null;
  latest_readiness_assessed_at: string | null;
  planning_approval_count: number;
  latest_planning_approval_id: string | null;
  latest_planning_approval_readiness_id: string | null;
  latest_planning_decision: "approved_for_planning" | "changes_requested" | "rejected" | null;
  latest_planning_decision_rationale: string | null;
  latest_planning_decided_at: string | null;
  operational_approval_satisfied: false;
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
  const effectiveRecommendation = value.latest_review_decision === "adjusted"
    ? value.latest_adjusted_recommendation
    : value.latest_review_decision === "accepted" ? value.recommendation : null;
  const mowingOrderConsistent = value.prepared_mowing_order_id === null
    ? value.mowing_order_state === "not_prepared"
    : typeof value.prepared_mowing_order_id === "string" &&
      value.mowing_order_state === "prepared_no_execution_authorization" &&
      effectiveRecommendation === "mowing_review";
  const resourceMetadata = [
    value.latest_resource_plan_id, value.latest_team_reference,
    value.latest_equipment_reference, value.latest_resource_plan_rationale,
    value.latest_resource_plan_created_at,
  ];
  const resourcePlanConsistent = value.resource_plan_count === 0
    ? resourceMetadata.every((item) => item === null)
    : typeof value.resource_plan_count === "number" && value.resource_plan_count > 0 &&
      value.prepared_mowing_order_id !== null &&
      resourceMetadata.every((item) => typeof item === "string");
  const readinessMetadata = [
    value.latest_readiness_assessment_id, value.latest_readiness_resource_plan_id,
    value.latest_weather_source_reference, value.latest_safety_source_reference,
    value.latest_readiness_rationale, value.latest_readiness_assessed_at,
  ];
  const readinessConsistent = value.readiness_assessment_count === 0
    ? readinessMetadata.every((item) => item === null) &&
      value.latest_weather_result === null && value.latest_safety_result === null
    : typeof value.readiness_assessment_count === "number" &&
      value.readiness_assessment_count > 0 &&
      readinessMetadata.every((item) => typeof item === "string") &&
      value.latest_readiness_resource_plan_id === value.latest_resource_plan_id &&
      ["clear", "blocked", "inconclusive"].includes(String(value.latest_weather_result)) &&
      ["clear", "blocked", "inconclusive"].includes(String(value.latest_safety_result));
  const approvalMetadata = [value.latest_planning_approval_id,
    value.latest_planning_approval_readiness_id, value.latest_planning_decision_rationale,
    value.latest_planning_decided_at];
  const approvalConsistent = value.planning_approval_count === 0
    ? approvalMetadata.every((item) => item === null) && value.latest_planning_decision === null
    : typeof value.planning_approval_count === "number" && value.planning_approval_count > 0 &&
      approvalMetadata.every((item) => typeof item === "string") &&
      value.latest_planning_approval_readiness_id === value.latest_readiness_assessment_id &&
      ["approved_for_planning", "changes_requested", "rejected"].includes(
        String(value.latest_planning_decision),
      );
  return [10, 30].includes(threshold) && value.threshold_exceeded === exceeded &&
    typeof value.review_count === "number" && Number.isInteger(value.review_count) &&
    reviewConsistent && mowingOrderConsistent && resourcePlanConsistent && readinessConsistent &&
    approvalConsistent && value.operational_approval_satisfied === false &&
    Number.isInteger(value.resource_plan_count) &&
    Number.isInteger(value.readiness_assessment_count) &&
    Number.isInteger(value.planning_approval_count) &&
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
