import { describe, expect, it } from "vitest";
import { isMowingPostServiceExceptionCollection } from "./mowing-post-service-exceptions";

const item = {
  exception_id: "99000000-0000-4000-8000-000000000002",
  summary_id: "98000000-0000-4000-8000-000000000002",
  mowing_order_id: "98000000-0000-4000-8000-000000000001",
  road_code: "SP-021",
  segment_index: 195,
  zone_type: "special",
  policy_version: "prepared-mowing-post-service-exception-v1",
  creation_rationale: "Avaliar pós-serviço simulado",
  recommendation: "inspect_follow_up",
  applicable_threshold_cm: "10",
  maximum_height_cm: "12",
  threshold_exceeded: true,
  requires_human_review: true,
  phase: "post_service",
  data_status: "simulated",
  location_status: "not_collected",
  evidence_status: "simulated_reviewed_non_operational",
  eligible_for_model_training: false,
  eligible_for_official_reporting: false,
  authorizes_field_work: false,
  created_at: "2026-08-13T12:00:00Z",
  review_count: 0,
  latest_review_id: null,
  latest_review_decision: null,
  latest_adjusted_recommendation: null,
  latest_review_rationale: null,
  latest_reviewed_at: null,
  review_state: "awaiting_review",
};

describe("mowing post-service exception contract", () => {
  it("accepts only simulated non-operational threshold assessments", () => {
    expect(isMowingPostServiceExceptionCollection({
      items: [item],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Simulated post-service exceptions only request human follow-up review.",
    })).toBe(true);
  });

  it("rejects promoted or inconsistent recommendations", () => {
    expect(isMowingPostServiceExceptionCollection({
      items: [{ ...item, authorizes_field_work: true }],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Simulated post-service exceptions only request human follow-up review.",
    })).toBe(false);
    expect(isMowingPostServiceExceptionCollection({
      items: [{ ...item, recommendation: "monitor" }],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Simulated post-service exceptions only request human follow-up review.",
    })).toBe(false);
  });

  it("accepts reviewed exceptions only with coherent effective review metadata", () => {
    expect(isMowingPostServiceExceptionCollection({
      items: [{
        ...item,
        review_count: 1,
        latest_review_id: "99000000-0000-4000-8000-000000000099",
        latest_review_decision: "adjusted",
        latest_adjusted_recommendation: "monitor",
        latest_review_rationale: "Registrar monitoramento após nova leitura humana.",
        latest_reviewed_at: "2026-08-13T12:30:00Z",
        review_state: "review_recorded_no_work_authorization",
      }],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Simulated post-service exceptions only request human follow-up review.",
    })).toBe(true);
    expect(isMowingPostServiceExceptionCollection({
      items: [{
        ...item,
        review_count: 1,
        latest_review_id: "99000000-0000-4000-8000-000000000099",
        latest_review_decision: "accepted",
        latest_adjusted_recommendation: "monitor",
        latest_review_rationale: null,
        latest_reviewed_at: "2026-08-13T12:30:00Z",
        review_state: "review_recorded_no_work_authorization",
      }],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Simulated post-service exceptions only request human follow-up review.",
    })).toBe(false);
  });
});
