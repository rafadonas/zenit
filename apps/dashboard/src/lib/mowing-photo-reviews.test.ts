import { describe, expect, it } from "vitest";
import { isMowingPhotoReviewQueue } from "./mowing-photo-reviews";

const base = {
  photo_id: "41000000-0000-0000-0000-000000000007", mowing_order_id: "41000000-0000-0000-0000-000000000008", source_inspection_work_order_id: "41000000-0000-0000-0000-000000000009", road_code: "SP021", segment_index: 195, zone_type: "left", planned_point_sequence: 1, captured_at: "2026-08-12T12:00:00Z", uploaded_at: "2026-08-12T12:01:00Z", media_type: "image/jpeg", byte_size: 4, latest_review_id: null, latest_decision: null, latest_quality_status: null, latest_ruler_status: null, latest_rationale: null, latest_reviewed_at: null, latest_review_policy_version: null, review_state: "awaiting_review", phase: "post_service", photo_scope: "mowing_demo_post_service_only", location_status: "not_collected", data_status: "simulated", operational_approval_satisfied: false, eligible_for_field_evidence: false, eligible_for_field_execution: false, eligible_for_model_training: false, eligible_for_official_reporting: false, authorizes_field_work: false,
};

describe("mowing photo review contract", () => {
  it("accepts the simulated awaiting-review shape", () => expect(isMowingPhotoReviewQueue({ items: [base], result_count: 1, limit: 50, truncated: false, warning: "safe" })).toBe(true));
  it("rejects a response that promotes data or authorizes work", () => expect(isMowingPhotoReviewQueue({ items: [{ ...base, data_status: "prepared" }], result_count: 1, limit: 50, truncated: false, warning: "unsafe" })).toBe(false));
});
