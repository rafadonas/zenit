import Link from "next/link";

import { DashboardHeader } from "../../components/dashboard-header";
import { Alert, DataStatus, EmptyState, ErrorState } from "../../components/ui";
import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  buildOverviewMetrics,
  latestOverviewReference,
  nextDecisionItem,
  recommendationLabel,
  shortcutsForRole,
  zoneLabel,
} from "../../lib/overview";
import {
  isRecommendationQueue,
  type RecommendationQueue,
} from "../../lib/recommendations";
import { isSegmentCollection, type SegmentCollection } from "../../lib/segments";

export const dynamic = "force-dynamic";

const FULL_CORRIDOR_BBOX = {
  min_lon: -46.84,
  min_lat: -23.64,
  max_lon: -46.72,
  max_lat: -23.4,
};

function displayDataStatus(status: string): "real" | "estimated" | "simulated" | "prepared" | "inconclusive" {
  if (status === "real" || status === "estimated" || status === "simulated" || status === "prepared") {
    return status;
  }
  return "inconclusive";
}

async function loadRecommendations(): Promise<RecommendationQueue> {
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/recommendations?limit=50`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Recommendation API returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isRecommendationQueue(payload)) {
    throw new Error("Recommendation API returned an invalid safety contract");
  }
  return payload;
}

async function loadSegments(): Promise<SegmentCollection> {
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const search = new URLSearchParams(
    Object.entries(FULL_CORRIDOR_BBOX).map(([key, value]) => [key, String(value)]),
  );
  const response = await fetch(`${baseUrl}/v1/roads/SP021/segments?${search}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Segment API returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isSegmentCollection(payload)) {
    throw new Error("Segment API returned an invalid GeoJSON contract");
  }
  return payload;
}

export default async function OverviewPage() {
  const [segmentsResult, queueResult, session] = await Promise.all([
    loadSegments().then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ error, ok: false as const }),
    ),
    loadRecommendations().then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ error, ok: false as const }),
    ),
    loadDashboardSession(),
  ]);
  const segments = segmentsResult.ok ? segmentsResult.value : null;
  const queue = queueResult.ok ? queueResult.value : null;
  const items = queue?.items ?? [];
  const metrics = buildOverviewMetrics(segments?.features.length ?? 0, items);
  const reference = latestOverviewReference(items);
  const focus = nextDecisionItem(items);
  const primaryRole = session?.road_roles[0]?.role ?? null;
  const shortcuts = shortcutsForRole(primaryRole);
  const hasPartialError = !segmentsResult.ok || !queueResult.ok;

  return (
    <main className="overview-shell" data-zenit-smoke-page="overview" id="main-content" tabIndex={-1}>
      <DashboardHeader
        active="overview"
        context={{ label: "Rodovia", value: "SP021" }}
        session={session ? {
          csrfToken: session.csrfToken,
          displayName: session.user.display_name,
          roadRoles: session.road_roles.map((role) => ({
            dataStatus: role.data_status,
            roadCode: role.road_code,
            role: role.role,
          })),
        } : null}
      />

      <div className="overview-content">
        <section className="overview-hero">
          <div>
            <p className="eyebrow">Situação</p>
            <h1>
              {metrics.awaitingReview > 0
                ? `${metrics.awaitingReview} decisão(ões) aguardam revisão humana`
                : "Nenhuma decisão pendente nesta fila"}
            </h1>
            <p className="subtitle">
              Primeiro veja o estado da rodovia, depois os pontos de atenção e por fim a
              próxima ação permitida para o seu papel.
            </p>
          </div>
          <Alert tone={reference.isStale ? "near" : "normal"} title={reference.isStale ? "Referência temporal antiga" : "Referência temporal visível"}>
            Fonte: API interna do dashboard. Última aquisição: {reference.label}. Nenhuma ação libera trabalho de campo.
          </Alert>
        </section>

        {hasPartialError ? (
          <ErrorState
            className="overview-state"
            description="Parte dos dados da visão geral não carregou. Nenhum KPI foi presumido."
            title="Dados parcialmente indisponíveis"
          />
        ) : null}

        <section className="overview-metrics" aria-label="Indicadores com fonte e referência temporal">
          <article>
            <strong>{metrics.segmentCount}</strong>
            <span>trechos de 100 m</span>
            <small><DataStatus status="prepared" /> Fonte: segmentos SP021</small>
          </article>
          <article>
            <strong>{queue?.metadata.total_count ?? 0}</strong>
            <span>análises apresentadas</span>
            <small><DataStatus status={reference.latestAcquiredAt ? "estimated" : "inconclusive"} /> Ref.: {reference.label}</small>
          </article>
          <article>
            <strong>{metrics.awaitingReview}</strong>
            <span>decisões pendentes</span>
            <small><DataStatus status="prepared" /> Fila humana</small>
          </article>
          <article>
            <strong>{metrics.preparedInspectionOrders}</strong>
            <span>ordens preparadas</span>
            <small><DataStatus status="prepared" /> Não autorizam campo</small>
          </article>
        </section>

        <section className="workflow-panel" aria-labelledby="workflow-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Fluxo principal</p>
              <h2 id="workflow-title">Cinco etapas, uma história</h2>
            </div>
            <span className="flow-caption">Dados reais e preparados permanecem separados</span>
          </div>
          <ol className="workflow-steps">
            <li className="complete">
              <span>1</span><div><strong>Monitorar</strong><small>Satélite e histórico</small></div>
            </li>
            <li className="complete">
              <span>2</span><div><strong>Analisar</strong><small>Trecho e zona</small></div>
            </li>
            <li className="active">
              <span>3</span><div><strong>Decidir</strong><small>Aprovação humana</small></div>
            </li>
            <li>
              <span>4</span><div><strong>Inspecionar</strong><small>Fotos e medidas</small></div>
            </li>
            <li>
              <span>5</span><div><strong>Concluir</strong><small>Histórico e resultado</small></div>
            </li>
          </ol>
        </section>

        <section className="overview-grid">
          <article className="focus-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Atenção e próxima ação</p>
                <h2>{focus ? `Trecho #${focus.segment_index}` : "Fila concluída"}</h2>
              </div>
              {focus ? <DataStatus status={displayDataStatus(focus.zone_data_status)} /> : null}
            </div>
            {focus ? (
              <>
                <div className="focus-decision">
                  <div><span>Zona</span><strong>{zoneLabel(focus.zone_type)}</strong></div>
                  <div><span>Recomendação</span><strong>{recommendationLabel(focus.recommendation)}</strong></div>
                  <div><span>Estado</span><strong>Revisão humana necessária</strong></div>
                </div>
                <p>
                  A análise é inconclusiva. A pessoa responsável revisa a evidência antes de
                  preparar qualquer inspeção.
                </p>
                <div className="overview-actions">
                  <Link className="primary-button" href="/recommendations">Revisar decisão</Link>
                  <Link className="secondary-button" href={`/corridor?segment=${focus.segment_index}`}>
                    Ver no mapa
                  </Link>
                </div>
              </>
            ) : (
              <EmptyState
                description="Nenhuma recomendação exige ação nesta resposta da API."
                title="Sem item para decisão"
              />
            )}
          </article>

          <aside className="boundary-card" aria-labelledby="boundary-title">
            <p className="eyebrow">Atalhos por papel</p>
            <h2 id="boundary-title">{primaryRole === "manager" ? "Gestor" : primaryRole === "supervisor" ? "Supervisor" : "Acesso público"}</h2>
            <ul>
              {shortcuts.map((shortcut) => (
                <li key={shortcut.href}>
                  <strong><Link href={shortcut.href}>{shortcut.label}</Link></strong>
                  <span>{shortcut.role === "public" ? "Disponível sem alterar dados." : "Ação limitada ao papel autenticado."}</span>
                </li>
              ))}
              <li><strong>Limite</strong><span>Sem KPI fictício, sem relatório oficial e sem autorização automática.</span></li>
            </ul>
          </aside>
        </section>
      </div>
    </main>
  );
}
