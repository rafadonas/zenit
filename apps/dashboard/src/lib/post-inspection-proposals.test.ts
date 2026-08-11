import { describe, expect, it } from "vitest";

import { isPreparedProposalCollection } from "./post-inspection-proposals";

const value = {
  items: [{
    proposal_id: "60000000-0000-4000-8000-000000000002",
    summary_id: "60000000-0000-4000-8000-000000000001",
    work_order_id: "60000000-0000-4000-8000-000000000003",
    road_code: "SP-021", segment_index: 195, zone_type: "special",
    policy_version: "prepared-post-inspection-v1",
    creation_rationale: "Aplicar regra preparada", recommendation: "mowing_review",
    applicable_threshold_cm: "10", maximum_height_cm: "35", threshold_exceeded: true,
    requires_human_review: true, location_status: "simulated",
    evidence_status: "prepared_reviewed_non_operational", data_status: "prepared",
    eligible_for_model_training: false, eligible_for_official_reporting: false,
    authorizes_field_work: false, created_at: "2026-08-11T17:00:00Z",
    review_count: 0, latest_review_id: null, latest_review_decision: null,
    latest_adjusted_recommendation: null, latest_review_rationale: null,
    latest_reviewed_at: null, review_state: "awaiting_review",
    prepared_mowing_order_id: null, mowing_order_state: "not_prepared",
  }], result_count: 1, limit: 50, truncated: false,
  warning: "Requires human review and never authorizes mowing.",
};

describe("prepared post-inspection proposal contract", () => {
  it("requires human review and rejects field authorization", () => {
    expect(isPreparedProposalCollection(value)).toBe(true);
    expect(isPreparedProposalCollection({
      ...value, items: [{ ...value.items[0], authorizes_field_work: true }],
    })).toBe(false);
    expect(isPreparedProposalCollection({
      ...value, items: [{ ...value.items[0], recommendation: "monitor" }],
    })).toBe(false);
    expect(isPreparedProposalCollection({
      ...value, items: [{ ...value.items[0], review_count: 1 }],
    })).toBe(false);
    expect(isPreparedProposalCollection({
      ...value, items: [{ ...value.items[0],
        prepared_mowing_order_id: "70000000-0000-4000-8000-000000000001",
        mowing_order_state: "prepared_no_execution_authorization" }],
    })).toBe(false);
  });
});
