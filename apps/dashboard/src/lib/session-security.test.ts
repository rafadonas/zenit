import { describe, expect, it } from "vitest";

import {
  csrfTokensMatch,
  getDashboardSecurityConfig,
  parseDecisionSubmission,
  parsePreparedInspectionOrderSubmission,
  parsePreparedMowingOrderSubmission,
  parsePhotoReviewSubmission,
  parsePreparedProposalSubmission,
  parsePreparedProposalReviewSubmission,
  parsePreparedSummaryExportSubmission,
  parsePreparedSummarySubmission,
  requestOriginMatches,
} from "./session-security";

const csrfToken = "a".repeat(64);

describe("dashboard session security", () => {
  it("requires HTTPS and secure cookies outside local environments", () => {
    expect(() =>
      getDashboardSecurityConfig({
        DASHBOARD_APP_ENV: "production",
        DASHBOARD_COOKIE_SECURE: "false",
        DASHBOARD_PUBLIC_ORIGIN: "http://dashboard.example.test",
      }),
    ).toThrow(/HTTPS/);
  });

  it("accepts only the exact configured request origin", () => {
    expect(requestOriginMatches("http://localhost:3000", "http://localhost:3000")).toBe(true);
    expect(requestOriginMatches("http://attacker.test", "http://localhost:3000")).toBe(false);
    expect(requestOriginMatches(null, "http://localhost:3000")).toBe(false);
  });

  it("compares well-formed CSRF tokens and fails closed", () => {
    expect(csrfTokensMatch(csrfToken, csrfToken)).toBe(true);
    expect(csrfTokensMatch(csrfToken, "b".repeat(64))).toBe(false);
    expect(csrfTokensMatch("short", csrfToken)).toBe(false);
  });

  it("builds only an allowlisted accepted-decision payload", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("decision", "accepted");
    form.set("reviewer_subject", "forged-actor");

    expect(parseDecisionSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      decision: "accepted",
    });
  });

  it("requires a rationale and replacement for adjusted decisions", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("decision", "adjusted");
    form.set("adjusted_recommendation", "inspect");

    expect(parseDecisionSubmission(form)).toBeNull();
    form.set("rationale", "Confirmar em campo antes de qualquer intervenção");
    expect(parseDecisionSubmission(form)).toMatchObject({
      decision: "adjusted",
      adjustedRecommendation: "inspect",
      rationale: "Confirmar em campo antes de qualquer intervenção",
    });
  });

  it("allowlists a prepared inspection-order request and requires rationale", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("source_review_id", "20000000-0000-4000-8000-000000000001");
    form.set("planning_rationale", "Planejar três pontos para inspeção");
    form.set("authorizes_field_work", "true");

    expect(parsePreparedInspectionOrderSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      sourceReviewId: "20000000-0000-4000-8000-000000000001",
      planningRationale: "Planejar três pontos para inspeção",
    });
    form.set("planning_rationale", " ");
    expect(parsePreparedInspectionOrderSubmission(form)).toBeNull();
  });

  it("accepts only a consistent non-operational photo review", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("decision", "accepted");
    form.set("quality_status", "accepted");
    form.set("ruler_status", "visible");
    form.set("authorizes_field_work", "true");

    expect(parsePhotoReviewSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      decision: "accepted",
      qualityStatus: "accepted",
      rulerStatus: "visible",
    });
    form.set("ruler_status", "not_visible");
    expect(parsePhotoReviewSubmission(form)).toBeNull();
    form.set("decision", "rejected");
    expect(parsePhotoReviewSubmission(form)).toBeNull();
    form.set("rationale", "Régua ausente");
    expect(parsePhotoReviewSubmission(form)).toMatchObject({
      decision: "rejected",
      rulerStatus: "not_visible",
      rationale: "Régua ausente",
    });
  });

  it("allowlists a prepared summary rationale without status promotion fields", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("generation_rationale", "Consolidar retorno preparado");
    form.set("eligible_for_official_reporting", "true");

    expect(parsePreparedSummarySubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      generationRationale: "Consolidar retorno preparado",
    });
    form.set("generation_rationale", " ");
    expect(parsePreparedSummarySubmission(form)).toBeNull();
  });

  it("allowlists a prepared CSV export purpose and ignores promotion fields", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("export_purpose", "Compartilhar resultado preparado");
    form.set("eligible_for_official_reporting", "true");

    expect(parsePreparedSummaryExportSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      exportPurpose: "Compartilhar resultado preparado",
    });
    form.set("export_purpose", " ");
    expect(parsePreparedSummaryExportSubmission(form)).toBeNull();
  });

  it("allowlists a prepared post-inspection proposal rationale", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("creation_rationale", "Aplicar regra preparada ao retorno revisado");
    form.set("authorizes_field_work", "true");
    expect(parsePreparedProposalSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      creationRationale: "Aplicar regra preparada ao retorno revisado",
    });
  });

  it("requires consistent human decisions for prepared proposals", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("decision", "adjusted");
    form.set("adjusted_recommendation", "monitor");
    form.set("rationale", "Manter monitoramento no cenário preparado");
    form.set("authorizes_field_work", "true");
    expect(parsePreparedProposalReviewSubmission(form)).toMatchObject({
      decision: "adjusted",
      adjustedRecommendation: "monitor",
      rationale: "Manter monitoramento no cenário preparado",
    });
    form.delete("rationale");
    expect(parsePreparedProposalReviewSubmission(form)).toBeNull();
  });

  it("allowlists a prepared mowing-order request without execution fields", () => {
    const form = new FormData();
    form.set("csrf_token", csrfToken);
    form.set("idempotency_key", "10000000-0000-4000-8000-000000000001");
    form.set("source_review_id", "20000000-0000-4000-8000-000000000001");
    form.set("planning_rationale", "Preparar planejamento sem liberar execução");
    form.set("authorizes_field_work", "true");
    expect(parsePreparedMowingOrderSubmission(form)).toEqual({
      csrfToken,
      idempotencyKey: "10000000-0000-4000-8000-000000000001",
      sourceReviewId: "20000000-0000-4000-8000-000000000001",
      planningRationale: "Preparar planejamento sem liberar execução",
    });
    form.set("planning_rationale", " ");
    expect(parsePreparedMowingOrderSubmission(form)).toBeNull();
  });
});
