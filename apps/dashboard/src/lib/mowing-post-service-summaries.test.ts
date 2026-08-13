import { describe, expect, it } from "vitest";
import { isMowingPostServiceSummaryCollection } from "./mowing-post-service-summaries";

const item = {
  summary_id: "98000000-0000-4000-8000-000000000002",
  mowing_order_id: "98000000-0000-4000-8000-000000000001",
  summary_policy_version: "prepared-mowing-post-service-summary-v1",
  generation_rationale: "Consolidar retorno pós-serviço",
  measurement_count: 3,
  accepted_photo_review_count: 3,
  minimum_height_cm: "4.00",
  maximum_height_cm: "8.00",
  mean_height_cm: "6.0000",
  n1_count: 3,
  n2_count: 0,
  n3_count: 0,
  phase: "post_service",
  summary_scope: "mowing_demo_post_service_only",
  location_status: "not_collected",
  data_status: "simulated",
  evidence_status: "simulated_reviewed_non_operational",
  eligible_for_field_evidence: false,
  eligible_for_field_execution: false,
  eligible_for_model_training: false,
  eligible_for_official_reporting: false,
  authorizes_field_work: false,
  generated_at: "2026-08-12T12:00:00Z",
};

describe("mowing post-service summary contract", () => {
  it("accepts only the simulated non-operational collection", () => {
    expect(isMowingPostServiceSummaryCollection({
      items: [item],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Resumo pós-serviço simulado; não comprova roçada, eficácia, conclusão ou operação oficial.",
    })).toBe(true);
  });

  it("rejects promoted official-reporting summaries", () => {
    expect(isMowingPostServiceSummaryCollection({
      items: [{ ...item, eligible_for_official_reporting: true }],
      result_count: 1,
      limit: 50,
      truncated: false,
      warning: "Resumo pós-serviço simulado; não comprova roçada, eficácia, conclusão ou operação oficial.",
    })).toBe(false);
  });
});
