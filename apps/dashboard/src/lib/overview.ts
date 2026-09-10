import type { RecommendationQueueItem } from "./recommendations";

export interface OverviewMetrics {
  awaitingReview: number;
  preparedInspectionOrders: number;
  reviewedRecommendations: number;
  segmentCount: number;
}

export function buildOverviewMetrics(
  segmentCount: number,
  items: RecommendationQueueItem[],
): OverviewMetrics {
  return {
    segmentCount,
    awaitingReview: items.filter((item) => item.review_state === "awaiting_review").length,
    reviewedRecommendations: items.filter((item) => item.review_state !== "awaiting_review").length,
    preparedInspectionOrders: items.filter(
      (item) => item.prepared_inspection_order_id !== null,
    ).length,
  };
}

export function zoneLabel(zone: RecommendationQueueItem["zone_type"]): string {
  if (zone === "left") return "margem esquerda";
  if (zone === "right") return "margem direita";
  if (zone === "median") return "canteiro central";
  return "área especial";
}

export function recommendationLabel(
  recommendation: RecommendationQueueItem["recommendation"],
): string {
  if (recommendation === "inspect") return "Inspecionar";
  if (recommendation === "mowing_review") return "Avaliar roçada";
  return "Monitorar";
}
