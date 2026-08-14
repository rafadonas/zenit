import type { MowingPostServiceException } from "./mowing-post-service-exceptions";

export function mowingPostServiceExceptionHeadline(
  exception: MowingPostServiceException,
): string {
  if (exception.latest_review_decision === "adjusted") {
    return exception.latest_adjusted_recommendation === "inspect_follow_up"
      ? "Ajustada para inspeção de seguimento"
      : "Ajustada para monitoramento";
  }
  return exception.recommendation === "inspect_follow_up"
    ? "Inspeção de seguimento indicada"
    : "Monitoramento indicado";
}

export function mowingPostServiceExceptionEffectiveDecision(
  exception: MowingPostServiceException,
): string | null {
  if (!exception.latest_review_decision) return null;
  if (exception.latest_review_decision === "accepted") return "aceita";
  if (exception.latest_review_decision === "rejected") return "rejeitada";
  return exception.latest_adjusted_recommendation === "inspect_follow_up"
    ? "ajustada para inspeção de seguimento"
    : "ajustada para monitoramento";
}

export function mowingPostServiceExceptionReviewStatus(
  exception: MowingPostServiceException,
): string {
  return exception.review_state === "awaiting_review"
    ? "Revisão humana obrigatória"
    : "Revisão registrada";
}
