export interface MowingPhotoReviewQueueItem {
  photo_id: string; mowing_order_id: string; source_inspection_work_order_id: string;
  road_code: string; segment_index: number; zone_type: "left" | "right" | "median" | "special";
  planned_point_sequence: number; captured_at: string; uploaded_at: string;
  media_type: "image/jpeg" | "image/png"; byte_size: number;
  latest_review_id: string | null; latest_decision: "accepted" | "rejected" | "inconclusive" | null;
  latest_quality_status: "accepted" | "rejected" | "inconclusive" | null;
  latest_ruler_status: "visible" | "not_visible" | "inconclusive" | null;
  latest_rationale: string | null; latest_reviewed_at: string | null; latest_review_policy_version: string | null;
  review_state: "awaiting_review" | "review_recorded"; phase: "post_service";
  photo_scope: "mowing_demo_post_service_only"; location_status: "not_collected"; data_status: "simulated";
  operational_approval_satisfied: false; eligible_for_field_evidence: false; eligible_for_field_execution: false;
  eligible_for_model_training: false; eligible_for_official_reporting: false; authorizes_field_work: false;
}

export interface MowingPhotoReviewQueue { items: MowingPhotoReviewQueueItem[]; result_count: number; limit: number; truncated: boolean; warning: string; }

function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null; }

function isItem(value: unknown): value is MowingPhotoReviewQueueItem {
  if (!isRecord(value)) return false;
  const hasReview = value.review_state === "review_recorded";
  const reviewConsistent = hasReview
    ? typeof value.latest_review_id === "string" && ["accepted", "rejected", "inconclusive"].includes(String(value.latest_decision)) && ["accepted", "rejected", "inconclusive"].includes(String(value.latest_quality_status)) && ["visible", "not_visible", "inconclusive"].includes(String(value.latest_ruler_status)) && typeof value.latest_reviewed_at === "string" && typeof value.latest_review_policy_version === "string"
    : value.review_state === "awaiting_review" && value.latest_review_id === null && value.latest_decision === null && value.latest_quality_status === null && value.latest_ruler_status === null && value.latest_reviewed_at === null;
  return reviewConsistent && typeof value.photo_id === "string" && typeof value.mowing_order_id === "string" && typeof value.source_inspection_work_order_id === "string" && typeof value.road_code === "string" && typeof value.segment_index === "number" && ["left", "right", "median", "special"].includes(String(value.zone_type)) && Number.isInteger(value.planned_point_sequence) && typeof value.captured_at === "string" && typeof value.uploaded_at === "string" && ["image/jpeg", "image/png"].includes(String(value.media_type)) && typeof value.byte_size === "number" && value.phase === "post_service" && value.photo_scope === "mowing_demo_post_service_only" && value.location_status === "not_collected" && value.data_status === "simulated" && value.operational_approval_satisfied === false && value.eligible_for_field_evidence === false && value.eligible_for_field_execution === false && value.eligible_for_model_training === false && value.eligible_for_official_reporting === false && value.authorizes_field_work === false;
}

export function isMowingPhotoReviewQueue(value: unknown): value is MowingPhotoReviewQueue {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(isItem) && typeof value.result_count === "number" && typeof value.limit === "number" && typeof value.truncated === "boolean" && typeof value.warning === "string";
}
