import { describe, expect, it } from "vitest";

import { explanationReasons, isRecommendationQueue } from "./recommendations";

const item = {
  vegetation_analysis_id: "analysis-1",
  analysis_run_id: "run-1",
  segment_id: "segment-1",
  road_code: "SP021",
  segment_index: 195,
  zone_type: "left",
  zone_data_status: "prepared",
  acquired_at: "2026-07-29T13:18:42Z",
  recommendation: "inspect",
  conclusion: "inconclusive",
  confidence_band: "low",
  explanation: { reasons: ["Prepared geometry.", "Field inspection required."] },
  rule_version: "rule-v1",
  processor_version: "processor-v1",
  requires_human_approval: true,
  eligible_for_official_reporting: false,
  review_count: 0,
  latest_review_id: null,
  latest_review_decision: null,
  latest_review_adjusted_recommendation: null,
  latest_reviewed_at: null,
  latest_review_policy_version: null,
  latest_review_policy_data_status: null,
  prepared_inspection_order_id: null,
  review_state: "awaiting_review",
  authorizes_field_work: false,
};

const metadata = {
  result_count: 1,
  total_count: 1,
  limit: 50,
  truncated: false,
  warning: "A review is not authorization.",
};

describe("recommendation queue contract", () => {
  it("accepts a non-authorizing queue item", () => {
    expect(isRecommendationQueue({ items: [item], metadata })).toBe(true);
  });

  it("accepts a recorded review only with a visible prepared policy", () => {
    const reviewedItem = {
      ...item,
      review_count: 1,
      latest_review_id: "review-1",
      latest_review_decision: "accepted",
      latest_reviewed_at: "2026-08-08T12:00:00Z",
      latest_review_policy_version: "recommendation-review-mvp-v1",
      latest_review_policy_data_status: "prepared",
      review_state: "review_recorded_no_work_authorization",
    };

    expect(isRecommendationQueue({ items: [reviewedItem], metadata })).toBe(true);
  });

  it("accepts a prepared order only for an effective inspection decision", () => {
    const reviewedItem = {
      ...item,
      review_count: 1,
      latest_review_id: "review-1",
      latest_review_decision: "accepted",
      latest_reviewed_at: "2026-08-08T12:00:00Z",
      latest_review_policy_version: "recommendation-review-mvp-v1",
      latest_review_policy_data_status: "prepared",
      prepared_inspection_order_id: "order-1",
      review_state: "review_recorded_no_work_authorization",
    };

    expect(isRecommendationQueue({ items: [reviewedItem], metadata })).toBe(true);
    expect(
      isRecommendationQueue({
        items: [{ ...reviewedItem, recommendation: "monitor" }],
        metadata,
      }),
    ).toBe(false);
  });

  it("fails closed if an item claims field authorization", () => {
    expect(
      isRecommendationQueue({ items: [{ ...item, authorizes_field_work: true }], metadata }),
    ).toBe(false);
  });

  it("extracts only textual explanation reasons", () => {
    expect(explanationReasons({ reasons: ["One", 2, null, "Two"] })).toEqual([
      "One",
      "Two",
    ]);
  });
});
