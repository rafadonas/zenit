export interface PhotoReviewQueueItem {
  photo_id: string;
  work_order_id: string;
  road_code: string;
  segment_index: number;
  zone_type: "left" | "right" | "median" | "special";
  planned_point_sequence: number;
  captured_at: string;
  uploaded_at: string;
  media_type: "image/jpeg" | "image/png";
  byte_size: number;
  latest_review_id: string | null;
  latest_decision: "accepted" | "rejected" | "inconclusive" | null;
  latest_quality_status: "accepted" | "rejected" | "inconclusive" | null;
  latest_ruler_status: "visible" | "not_visible" | "inconclusive" | null;
  latest_rationale: string | null;
  latest_reviewed_at: string | null;
  latest_review_policy_version: string | null;
  review_state: "awaiting_review" | "review_recorded";
  data_status: "prepared";
  eligible_for_field_evidence: false;
  eligible_for_model_training: false;
  eligible_for_official_reporting: false;
  authorizes_field_work: false;
}

export interface PhotoReviewQueue {
  items: PhotoReviewQueueItem[];
  result_count: number;
  limit: number;
  truncated: boolean;
  warning: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isItem(value: unknown): value is PhotoReviewQueueItem {
  if (!isRecord(value)) return false;
  const awaiting = value.review_state === "awaiting_review";
  const reviewConsistent = awaiting
    ? value.latest_review_id === null && value.latest_decision === null &&
      value.latest_quality_status === null && value.latest_ruler_status === null &&
      value.latest_rationale === null && value.latest_reviewed_at === null &&
      value.latest_review_policy_version === null
    : value.review_state === "review_recorded" &&
      typeof value.latest_review_id === "string" &&
      ["accepted", "rejected", "inconclusive"].includes(String(value.latest_decision)) &&
      ["accepted", "rejected", "inconclusive"].includes(String(value.latest_quality_status)) &&
      ["visible", "not_visible", "inconclusive"].includes(String(value.latest_ruler_status)) &&
      typeof value.latest_reviewed_at === "string" &&
      typeof value.latest_review_policy_version === "string";
  return reviewConsistent &&
    typeof value.photo_id === "string" && typeof value.work_order_id === "string" &&
    typeof value.road_code === "string" && typeof value.segment_index === "number" &&
    ["left", "right", "median", "special"].includes(String(value.zone_type)) &&
    Number.isInteger(value.planned_point_sequence) &&
    typeof value.captured_at === "string" && typeof value.uploaded_at === "string" &&
    ["image/jpeg", "image/png"].includes(String(value.media_type)) &&
    typeof value.byte_size === "number" && value.data_status === "prepared" &&
    value.eligible_for_field_evidence === false &&
    value.eligible_for_model_training === false &&
    value.eligible_for_official_reporting === false && value.authorizes_field_work === false;
}

export function isPhotoReviewQueue(value: unknown): value is PhotoReviewQueue {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(isItem) &&
    typeof value.result_count === "number" && typeof value.limit === "number" &&
    typeof value.truncated === "boolean" && typeof value.warning === "string";
}
