export interface RecommendationQueueItem {
  vegetation_analysis_id: string;
  analysis_run_id: string;
  segment_id: string;
  road_code: string;
  segment_index: number;
  zone_type: "left" | "right" | "median" | "special";
  zone_data_status: string;
  acquired_at: string;
  recommendation: "monitor" | "inspect" | "mowing_review";
  conclusion: "conclusive" | "inconclusive";
  confidence_band: "low" | "medium" | "high";
  explanation: Record<string, unknown>;
  rule_version: string;
  processor_version: string;
  requires_human_approval: boolean;
  eligible_for_official_reporting: boolean;
  review_count: number;
  latest_review_id: string | null;
  latest_review_decision: "accepted" | "rejected" | "adjusted" | null;
  latest_review_adjusted_recommendation: "monitor" | "inspect" | "mowing_review" | null;
  latest_reviewed_at: string | null;
  latest_review_policy_version: string | null;
  latest_review_policy_data_status: "prepared" | "real" | null;
  prepared_inspection_order_id: string | null;
  review_state:
    | "awaiting_review"
    | "review_recorded_policy_pending"
    | "review_recorded_no_work_authorization";
  authorizes_field_work: false;
}

export interface RecommendationQueue {
  items: RecommendationQueueItem[];
  metadata: {
    result_count: number;
    total_count: number;
    limit: number;
    truncated: boolean;
    warning: string;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isQueueItem(value: unknown): value is RecommendationQueueItem {
  if (!isRecord(value) || !isRecord(value.explanation)) return false;
  const reviewMetadataIsConsistent = value.review_count === 0
    ? value.latest_review_decision === null &&
      value.latest_review_id === null &&
      value.latest_review_adjusted_recommendation === null &&
      value.latest_reviewed_at === null &&
      value.latest_review_policy_version === null &&
      value.latest_review_policy_data_status === null &&
      value.prepared_inspection_order_id === null &&
      value.review_state === "awaiting_review"
    : value.latest_review_decision !== null &&
      typeof value.latest_review_id === "string" &&
      typeof value.latest_reviewed_at === "string" &&
      (value.latest_review_policy_version === null
        ? value.latest_review_policy_data_status === null &&
          value.review_state === "review_recorded_policy_pending"
        : typeof value.latest_review_policy_version === "string" &&
          ["prepared", "real"].includes(String(value.latest_review_policy_data_status)) &&
          value.review_state === "review_recorded_no_work_authorization");
  const adjustedDecisionIsConsistent = value.latest_review_decision === "adjusted"
    ? ["monitor", "inspect", "mowing_review"].includes(
        String(value.latest_review_adjusted_recommendation),
      )
    : value.latest_review_adjusted_recommendation === null;
  const effectiveAction = value.latest_review_decision === "adjusted"
    ? value.latest_review_adjusted_recommendation
    : value.latest_review_decision === "accepted"
      ? value.recommendation
      : null;
  const preparedOrderIsConsistent = value.prepared_inspection_order_id === null ||
    (typeof value.prepared_inspection_order_id === "string" && effectiveAction === "inspect");
  return (
    typeof value.vegetation_analysis_id === "string" &&
    typeof value.analysis_run_id === "string" &&
    typeof value.segment_id === "string" &&
    typeof value.road_code === "string" &&
    isFiniteNumber(value.segment_index) &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    typeof value.zone_data_status === "string" &&
    typeof value.acquired_at === "string" &&
    ["monitor", "inspect", "mowing_review"].includes(String(value.recommendation)) &&
    ["conclusive", "inconclusive"].includes(String(value.conclusion)) &&
    ["low", "medium", "high"].includes(String(value.confidence_band)) &&
    typeof value.rule_version === "string" &&
    typeof value.processor_version === "string" &&
    typeof value.requires_human_approval === "boolean" &&
    typeof value.eligible_for_official_reporting === "boolean" &&
    isFiniteNumber(value.review_count) &&
    (value.latest_review_id === null || typeof value.latest_review_id === "string") &&
    [null, "accepted", "rejected", "adjusted"].includes(
      value.latest_review_decision as null | string,
    ) &&
    [null, "monitor", "inspect", "mowing_review"].includes(
      value.latest_review_adjusted_recommendation as null | string,
    ) &&
    (value.latest_reviewed_at === null || typeof value.latest_reviewed_at === "string") &&
    (value.latest_review_policy_version === null ||
      typeof value.latest_review_policy_version === "string") &&
    [null, "prepared", "real"].includes(
      value.latest_review_policy_data_status as null | string,
    ) &&
    [
      "awaiting_review",
      "review_recorded_policy_pending",
      "review_recorded_no_work_authorization",
    ].includes(
      String(value.review_state),
    ) &&
    reviewMetadataIsConsistent &&
    adjustedDecisionIsConsistent &&
    preparedOrderIsConsistent &&
    value.authorizes_field_work === false
  );
}

export function isRecommendationQueue(value: unknown): value is RecommendationQueue {
  if (!isRecord(value) || !Array.isArray(value.items) || !isRecord(value.metadata)) {
    return false;
  }
  return (
    value.items.every(isQueueItem) &&
    isFiniteNumber(value.metadata.result_count) &&
    isFiniteNumber(value.metadata.total_count) &&
    isFiniteNumber(value.metadata.limit) &&
    typeof value.metadata.truncated === "boolean" &&
    typeof value.metadata.warning === "string"
  );
}

export function explanationReasons(explanation: Record<string, unknown>): string[] {
  const reasons = explanation.reasons;
  if (!Array.isArray(reasons)) return [];
  return reasons.filter((reason): reason is string => typeof reason === "string");
}
