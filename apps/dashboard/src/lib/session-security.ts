import { timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE_NAME = "zenit_session";
export const CSRF_COOKIE_NAME = "zenit_csrf";

export interface DashboardSecurityConfig {
  appEnvironment: "development" | "test" | "demo" | "staging" | "production";
  publicOrigin: string;
  secureCookies: boolean;
}

export interface DecisionSubmission {
  csrfToken: string;
  idempotencyKey: string;
  decision: "accepted" | "rejected" | "adjusted";
  adjustedRecommendation?: "monitor" | "inspect" | "mowing_review";
  rationale?: string;
  supersedesReviewId?: string;
}

export interface PreparedInspectionOrderSubmission {
  csrfToken: string;
  idempotencyKey: string;
  sourceReviewId: string;
  planningRationale: string;
}

export interface PhotoReviewSubmission {
  csrfToken: string;
  idempotencyKey: string;
  decision: "accepted" | "rejected" | "inconclusive";
  qualityStatus: "accepted" | "rejected" | "inconclusive";
  rulerStatus: "visible" | "not_visible" | "inconclusive";
  rationale?: string;
  supersedesReviewId?: string;
}

export interface PreparedSummarySubmission {
  csrfToken: string;
  idempotencyKey: string;
  generationRationale: string;
}

export interface PreparedSummaryExportSubmission {
  csrfToken: string;
  idempotencyKey: string;
  exportPurpose: string;
}

export interface PreparedProposalSubmission {
  csrfToken: string;
  idempotencyKey: string;
  creationRationale: string;
}

export interface PreparedProposalReviewSubmission {
  csrfToken: string;
  idempotencyKey: string;
  decision: "accepted" | "rejected" | "adjusted";
  adjustedRecommendation?: "monitor" | "mowing_review";
  rationale?: string;
  supersedesReviewId?: string;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CSRF_PATTERN = /^[0-9a-f]{64}$/;

export function getDashboardSecurityConfig(
  environment: Readonly<Record<string, string | undefined>> = process.env,
): DashboardSecurityConfig {
  const appEnvironment = environment.DASHBOARD_APP_ENV ?? "development";
  if (!["development", "test", "demo", "staging", "production"].includes(appEnvironment)) {
    throw new Error("DASHBOARD_APP_ENV is invalid");
  }

  const configuredOrigin = environment.DASHBOARD_PUBLIC_ORIGIN ?? "http://localhost:3000";
  const originUrl = new URL(configuredOrigin);
  if (
    originUrl.origin !== configuredOrigin ||
    originUrl.username ||
    originUrl.password ||
    originUrl.search ||
    originUrl.hash
  ) {
    throw new Error("DASHBOARD_PUBLIC_ORIGIN must be an origin without credentials or a path");
  }

  const secureValue = environment.DASHBOARD_COOKIE_SECURE ?? "false";
  if (!["true", "false"].includes(secureValue)) {
    throw new Error("DASHBOARD_COOKIE_SECURE must be true or false");
  }
  const secureCookies = secureValue === "true";
  if (
    ["staging", "production"].includes(appEnvironment) &&
    (!secureCookies || originUrl.protocol !== "https:")
  ) {
    throw new Error("staging and production require HTTPS and secure dashboard cookies");
  }

  return {
    appEnvironment: appEnvironment as DashboardSecurityConfig["appEnvironment"],
    publicOrigin: originUrl.origin,
    secureCookies,
  };
}

export function requestOriginMatches(origin: string | null, expectedOrigin: string): boolean {
  if (origin === null) return false;
  try {
    return new URL(origin).origin === expectedOrigin && origin === expectedOrigin;
  } catch {
    return false;
  }
}

export function csrfTokensMatch(submitted: string | null, cookie: string | undefined): boolean {
  if (!submitted || !cookie || !CSRF_PATTERN.test(submitted) || !CSRF_PATTERN.test(cookie)) {
    return false;
  }
  return timingSafeEqual(Buffer.from(submitted, "hex"), Buffer.from(cookie, "hex"));
}

function formString(form: FormData, key: string): string | null {
  const value = form.get(key);
  return typeof value === "string" ? value.trim() : null;
}

export function parseDecisionSubmission(form: FormData): DecisionSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const decision = formString(form, "decision");
  const adjustedRecommendation = formString(form, "adjusted_recommendation");
  const rationale = formString(form, "rationale");
  const supersedesReviewId = formString(form, "supersedes_review_id");

  if (
    csrfToken === null ||
    !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null ||
    !UUID_PATTERN.test(idempotencyKey) ||
    !["accepted", "rejected", "adjusted"].includes(decision ?? "")
  ) {
    return null;
  }
  if (supersedesReviewId && !UUID_PATTERN.test(supersedesReviewId)) return null;

  if (decision === "adjusted") {
    if (
      !["monitor", "inspect", "mowing_review"].includes(adjustedRecommendation ?? "") ||
      !rationale
    ) {
      return null;
    }
  } else if (adjustedRecommendation) {
    return null;
  }
  if (decision === "rejected" && !rationale) return null;
  if (rationale && rationale.length > 2000) return null;

  return {
    csrfToken,
    idempotencyKey,
    decision: decision as DecisionSubmission["decision"],
    ...(adjustedRecommendation
      ? { adjustedRecommendation: adjustedRecommendation as NonNullable<DecisionSubmission["adjustedRecommendation"]> }
      : {}),
    ...(rationale ? { rationale } : {}),
    ...(supersedesReviewId ? { supersedesReviewId } : {}),
  };
}

export function parsePreparedInspectionOrderSubmission(
  form: FormData,
): PreparedInspectionOrderSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const sourceReviewId = formString(form, "source_review_id");
  const planningRationale = formString(form, "planning_rationale");
  if (
    csrfToken === null ||
    !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null ||
    !UUID_PATTERN.test(idempotencyKey) ||
    sourceReviewId === null ||
    !UUID_PATTERN.test(sourceReviewId) ||
    planningRationale === null ||
    planningRationale.length < 1 ||
    planningRationale.length > 2000
  ) {
    return null;
  }
  return { csrfToken, idempotencyKey, sourceReviewId, planningRationale };
}

export function isUuid(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function parsePhotoReviewSubmission(form: FormData): PhotoReviewSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const decision = formString(form, "decision");
  const qualityStatus = formString(form, "quality_status");
  const rulerStatus = formString(form, "ruler_status");
  const rationale = formString(form, "rationale");
  const supersedesReviewId = formString(form, "supersedes_review_id");
  if (
    csrfToken === null || !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null || !UUID_PATTERN.test(idempotencyKey) ||
    !["accepted", "rejected", "inconclusive"].includes(decision ?? "") ||
    !["accepted", "rejected", "inconclusive"].includes(qualityStatus ?? "") ||
    !["visible", "not_visible", "inconclusive"].includes(rulerStatus ?? "") ||
    (supersedesReviewId !== null && supersedesReviewId !== "" &&
      !UUID_PATTERN.test(supersedesReviewId)) ||
    (rationale !== null && rationale.length > 2000)
  ) return null;
  const acceptedEvidence = qualityStatus === "accepted" && rulerStatus === "visible";
  if ((decision === "accepted") !== acceptedEvidence) return null;
  if (decision !== "accepted" && !rationale) return null;
  return {
    csrfToken,
    idempotencyKey,
    decision: decision as PhotoReviewSubmission["decision"],
    qualityStatus: qualityStatus as PhotoReviewSubmission["qualityStatus"],
    rulerStatus: rulerStatus as PhotoReviewSubmission["rulerStatus"],
    ...(rationale ? { rationale } : {}),
    ...(supersedesReviewId ? { supersedesReviewId } : {}),
  };
}

export function parsePreparedSummarySubmission(form: FormData): PreparedSummarySubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const generationRationale = formString(form, "generation_rationale");
  if (
    csrfToken === null || !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null || !UUID_PATTERN.test(idempotencyKey) ||
    generationRationale === null || generationRationale.length < 1 ||
    generationRationale.length > 2000
  ) return null;
  return { csrfToken, idempotencyKey, generationRationale };
}

export function parsePreparedSummaryExportSubmission(
  form: FormData,
): PreparedSummaryExportSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const exportPurpose = formString(form, "export_purpose");
  if (
    csrfToken === null || !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null || !UUID_PATTERN.test(idempotencyKey) ||
    exportPurpose === null || exportPurpose.length < 1 || exportPurpose.length > 2000
  ) return null;
  return { csrfToken, idempotencyKey, exportPurpose };
}

export function parsePreparedProposalSubmission(form: FormData): PreparedProposalSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const creationRationale = formString(form, "creation_rationale");
  if (
    csrfToken === null || !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null || !UUID_PATTERN.test(idempotencyKey) ||
    creationRationale === null || creationRationale.length < 1 || creationRationale.length > 2000
  ) return null;
  return { csrfToken, idempotencyKey, creationRationale };
}

export function parsePreparedProposalReviewSubmission(
  form: FormData,
): PreparedProposalReviewSubmission | null {
  const csrfToken = formString(form, "csrf_token");
  const idempotencyKey = formString(form, "idempotency_key");
  const decision = formString(form, "decision");
  const adjustedRecommendation = formString(form, "adjusted_recommendation");
  const rationale = formString(form, "rationale");
  const supersedesReviewId = formString(form, "supersedes_review_id");
  if (
    csrfToken === null || !CSRF_PATTERN.test(csrfToken) ||
    idempotencyKey === null || !UUID_PATTERN.test(idempotencyKey) ||
    !["accepted", "rejected", "adjusted"].includes(decision ?? "") ||
    (supersedesReviewId !== null && supersedesReviewId !== "" &&
      !UUID_PATTERN.test(supersedesReviewId)) || (rationale !== null && rationale.length > 2000)
  ) return null;
  const isAdjusted = decision === "adjusted";
  if (isAdjusted !== ["monitor", "mowing_review"].includes(adjustedRecommendation ?? "")) {
    return null;
  }
  if ((decision === "rejected" || isAdjusted) && !rationale) return null;
  return {
    csrfToken, idempotencyKey,
    decision: decision as PreparedProposalReviewSubmission["decision"],
    ...(adjustedRecommendation ? {
      adjustedRecommendation: adjustedRecommendation as "monitor" | "mowing_review",
    } : {}),
    ...(rationale ? { rationale } : {}),
    ...(supersedesReviewId ? { supersedesReviewId } : {}),
  };
}
