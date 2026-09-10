import { describe, expect, it } from "vitest";

import type { RecommendationQueueItem } from "./recommendations";
import { buildOverviewMetrics, recommendationLabel, zoneLabel } from "./overview";

function item(
  reviewState: RecommendationQueueItem["review_state"],
  preparedInspectionOrderId: string | null = null,
): RecommendationQueueItem {
  return {
    vegetation_analysis_id: "analysis",
    analysis_run_id: "run",
    segment_id: "segment",
    road_code: "SP021",
    segment_index: 195,
    zone_type: "left",
    zone_data_status: "prepared",
    acquired_at: "2026-07-29T00:00:00Z",
    recommendation: "inspect",
    conclusion: "inconclusive",
    confidence_band: "low",
    explanation: {},
    rule_version: "rules-v1",
    processor_version: "processor-v1",
    requires_human_approval: true,
    eligible_for_official_reporting: false,
    review_count: reviewState === "awaiting_review" ? 0 : 1,
    latest_review_id: reviewState === "awaiting_review" ? null : "review",
    latest_review_decision: reviewState === "awaiting_review" ? null : "accepted",
    latest_review_adjusted_recommendation: null,
    latest_reviewed_at: reviewState === "awaiting_review" ? null : "2026-08-19T00:00:00Z",
    latest_review_policy_version: reviewState === "awaiting_review" ? null : "policy-v1",
    latest_review_policy_data_status: reviewState === "awaiting_review" ? null : "prepared",
    prepared_inspection_order_id: preparedInspectionOrderId,
    review_state: reviewState,
    authorizes_field_work: false,
  };
}

describe("overview presentation", () => {
  it("summarizes the demo without changing domain state", () => {
    const metrics = buildOverviewMetrics(309, [
      item("awaiting_review"),
      item("review_recorded_no_work_authorization", "order"),
    ]);

    expect(metrics).toEqual({
      segmentCount: 309,
      awaitingReview: 1,
      reviewedRecommendations: 1,
      preparedInspectionOrders: 1,
    });
  });

  it("translates domain labels for the presentation layer", () => {
    expect(zoneLabel("left")).toBe("margem esquerda");
    expect(zoneLabel("special")).toBe("área especial");
    expect(recommendationLabel("inspect")).toBe("Inspecionar");
    expect(recommendationLabel("mowing_review")).toBe("Avaliar roçada");
  });
});
