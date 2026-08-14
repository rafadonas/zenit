import { describe, expect, it } from "vitest";

import {
  mowingPostServiceExceptionEffectiveDecision,
  mowingPostServiceExceptionHeadline,
  mowingPostServiceExceptionReviewStatus,
} from "./mowing-post-service-exception-presenter";

const baseException = {
  exception_id: "99000000-0000-4000-8000-000000000002",
  summary_id: "98000000-0000-4000-8000-000000000002",
  mowing_order_id: "98000000-0000-4000-8000-000000000001",
  road_code: "SP-021",
  segment_index: 195,
  zone_type: "special" as const,
  policy_version: "prepared-mowing-post-service-exception-v1",
  creation_rationale: "Avaliar pós-serviço simulado",
  recommendation: "inspect_follow_up" as const,
  applicable_threshold_cm: "10",
  maximum_height_cm: "12",
  threshold_exceeded: true,
  requires_human_review: true as const,
  phase: "post_service" as const,
  data_status: "simulated" as const,
  location_status: "not_collected" as const,
  evidence_status: "simulated_reviewed_non_operational" as const,
  eligible_for_model_training: false as const,
  eligible_for_official_reporting: false as const,
  authorizes_field_work: false as const,
  created_at: "2026-08-13T12:00:00Z",
  review_count: 0,
  latest_review_id: null,
  latest_review_decision: null,
  latest_adjusted_recommendation: null,
  latest_review_rationale: null,
  latest_reviewed_at: null,
  review_state: "awaiting_review" as const,
};

describe("mowing post-service exception presenter", () => {
  it("shows the base recommendation while review is pending", () => {
    expect(mowingPostServiceExceptionHeadline(baseException)).toBe(
      "Inspeção de seguimento indicada",
    );
    expect(mowingPostServiceExceptionEffectiveDecision(baseException)).toBeNull();
    expect(mowingPostServiceExceptionReviewStatus(baseException)).toBe(
      "Revisão humana obrigatória",
    );
  });

  it("shows accepted and rejected effective decisions", () => {
    expect(mowingPostServiceExceptionEffectiveDecision({
      ...baseException,
      review_count: 1,
      latest_review_id: "99000000-0000-4000-8000-000000000099",
      latest_review_decision: "accepted",
      latest_reviewed_at: "2026-08-13T12:30:00Z",
      review_state: "review_recorded_no_work_authorization",
    })).toBe("aceita");
    expect(mowingPostServiceExceptionEffectiveDecision({
      ...baseException,
      review_count: 1,
      latest_review_id: "99000000-0000-4000-8000-000000000099",
      latest_review_decision: "rejected",
      latest_review_rationale: "Manter apenas histórico simulado.",
      latest_reviewed_at: "2026-08-13T12:30:00Z",
      review_state: "review_recorded_no_work_authorization",
    })).toBe("rejeitada");
  });

  it("shows adjusted outcomes and recorded status", () => {
    const adjusted = {
      ...baseException,
      review_count: 1,
      latest_review_id: "99000000-0000-4000-8000-000000000099",
      latest_review_decision: "adjusted" as const,
      latest_adjusted_recommendation: "monitor" as const,
      latest_review_rationale: "Manter monitoramento após revisão humana.",
      latest_reviewed_at: "2026-08-13T12:30:00Z",
      review_state: "review_recorded_no_work_authorization" as const,
    };
    expect(mowingPostServiceExceptionHeadline(adjusted)).toBe(
      "Ajustada para monitoramento",
    );
    expect(mowingPostServiceExceptionEffectiveDecision(adjusted)).toBe(
      "ajustada para monitoramento",
    );
    expect(mowingPostServiceExceptionReviewStatus(adjusted)).toBe("Revisão registrada");
  });
});
