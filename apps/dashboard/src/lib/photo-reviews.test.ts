import { describe, expect, it } from "vitest";

import { isPhotoReviewQueue } from "./photo-reviews";

const item = {
  photo_id: "photo", work_order_id: "order", road_code: "SP021", segment_index: 195,
  zone_type: "left", planned_point_sequence: 1, captured_at: "2026-08-11T10:00:00Z",
  uploaded_at: "2026-08-11T11:00:00Z", media_type: "image/jpeg", byte_size: 4,
  latest_review_id: null, latest_decision: null, latest_quality_status: null,
  latest_ruler_status: null, latest_rationale: null, latest_reviewed_at: null,
  latest_review_policy_version: null, review_state: "awaiting_review", data_status: "prepared",
  eligible_for_field_evidence: false, eligible_for_model_training: false,
  eligible_for_official_reporting: false, authorizes_field_work: false,
};

describe("photo review queue contract", () => {
  it("accepts a prepared awaiting item", () => {
    expect(isPhotoReviewQueue({ items: [item], result_count: 1, limit: 50, truncated: false, warning: "safe" })).toBe(true);
  });

  it("fails closed on operational or inconsistent claims", () => {
    expect(isPhotoReviewQueue({ items: [{ ...item, authorizes_field_work: true }], result_count: 1, limit: 50, truncated: false, warning: "safe" })).toBe(false);
    expect(isPhotoReviewQueue({ items: [{ ...item, review_state: "review_recorded" }], result_count: 1, limit: 50, truncated: false, warning: "safe" })).toBe(false);
  });
});
