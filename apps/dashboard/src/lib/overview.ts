import type { RecommendationQueueItem } from "./recommendations";

export interface OverviewMetrics {
  awaitingReview: number;
  preparedInspectionOrders: number;
  reviewedRecommendations: number;
  segmentCount: number;
}

export interface OverviewReference {
  isStale: boolean;
  label: string;
  latestAcquiredAt: string | null;
}

export type OverviewShortcut = {
  href: string;
  label: string;
  role: "manager" | "supervisor" | "public";
};

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

export function latestOverviewReference(
  items: RecommendationQueueItem[],
  now = new Date(),
): OverviewReference {
  const latestTime = items.reduce<number | null>((latest, item) => {
    const time = Date.parse(item.acquired_at);
    if (Number.isNaN(time)) return latest;
    return latest === null || time > latest ? time : latest;
  }, null);

  if (latestTime === null) {
    return {
      isStale: true,
      label: "Sem referência temporal",
      latestAcquiredAt: null,
    };
  }

  const daysOld = Math.floor((now.getTime() - latestTime) / 86_400_000);
  return {
    isStale: daysOld > 30,
    label: new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeZone: "America/Sao_Paulo",
    }).format(new Date(latestTime)),
    latestAcquiredAt: new Date(latestTime).toISOString(),
  };
}

export function nextDecisionItem(items: RecommendationQueueItem[]): RecommendationQueueItem | null {
  return items.find((item) => item.review_state === "awaiting_review") ?? items[0] ?? null;
}

export function shortcutsForRole(role: "manager" | "supervisor" | null): OverviewShortcut[] {
  if (role === "manager") {
    return [
      { href: "/recommendations", label: "Revisar decisões", role },
      { href: "/mowing-post-service-summaries", label: "Ver resultados", role },
    ];
  }
  if (role === "supervisor") {
    return [
      { href: "/photo-reviews", label: "Revisar fotos", role },
      { href: "/corridor", label: "Consultar mapa", role },
    ];
  }
  return [
    { href: "/login", label: "Entrar para operar", role: "public" },
    { href: "/corridor", label: "Ver mapa preparado", role: "public" },
  ];
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
