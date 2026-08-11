import { describe, expect, it } from "vitest";

import { isPreparedSummaryCollection } from "./prepared-summaries";

function collection() {
  return {
    items: [{
      summary_id: "50000000-0000-4000-8000-000000000002",
      work_order_id: "50000000-0000-4000-8000-000000000001",
      summary_policy_version: "prepared-inspection-summary-v1",
      generation_rationale: "Consolidar retorno preparado",
      measurement_count: 3, accepted_photo_review_count: 3,
      minimum_height_cm: "8", maximum_height_cm: "35", mean_height_cm: "21.6667",
      n1_count: 1, n2_count: 1, n3_count: 1,
      class_rule: "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm",
      location_status: "simulated", evidence_status: "prepared_reviewed_non_operational",
      data_status: "prepared", eligible_for_field_evidence: false,
      eligible_for_model_training: false, eligible_for_official_reporting: false,
      authorizes_field_work: false, generated_at: "2026-08-11T15:00:00Z",
    }],
    result_count: 1, limit: 50, truncated: false,
    warning: "Prepared summaries are not official reports.",
  };
}

describe("prepared summary safety contract", () => {
  it("accepts only the explicitly prepared and non-operational result", () => {
    expect(isPreparedSummaryCollection(collection())).toBe(true);
    const unsafe = collection();
    unsafe.items[0].eligible_for_official_reporting = true;
    expect(isPreparedSummaryCollection(unsafe)).toBe(false);
  });

  it("requires all three historical class counts", () => {
    const inconsistent = collection();
    inconsistent.items[0].n3_count = 2;
    expect(isPreparedSummaryCollection(inconsistent)).toBe(false);
  });
});
