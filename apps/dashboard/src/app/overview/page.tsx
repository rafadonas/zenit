import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  buildOverviewMetrics,
  recommendationLabel,
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
  const [segments, queue, session] = await Promise.all([
    loadSegments(),
    loadRecommendations(),
    loadDashboardSession(),
  ]);
  const metrics = buildOverviewMetrics(segments.features.length, queue.items);
  const focus = queue.items.find((item) => item.review_state === "awaiting_review") ?? queue.items[0];

  return (
    <main className="overview-shell" data-zenit-smoke-page="overview" id="main-content">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true"><i /></span>
          <div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div>
        </div>
        <nav className="topnav" aria-label="Navegação principal">
          <Link aria-current="page" href="/overview">Visão geral</Link>
          <Link href="/corridor">Mapa</Link>
          <Link href="/recommendations">Decisões</Link>
          <Link href="/photo-reviews">Campo</Link>
          <Link href="/mowing-post-service-summaries">Resultados</Link>
        </nav>
        {session ? (
          <div className="session-context">
            <span>{session.user.display_name}</span>
            <form action="/api/auth/logout" method="post">
              <input name="csrf_token" type="hidden" value={session.csrfToken} />
              <button type="submit">Sair</button>
            </form>
          </div>
        ) : null}
      </header>

      <div className="overview-content">
        <section className="overview-hero">
          <div>
            <p className="eyebrow">Demonstração do produto</p>
            <h1>Da imagem à decisão em campo</h1>
            <p className="subtitle">
              Uma visão simples do que foi detectado, do que precisa de decisão humana e do
              que ainda depende de validação.
            </p>
          </div>
          <div className="demo-state" role="status">
            <span>Ambiente preparado</span>
            <strong>Nenhuma ação libera trabalho de campo</strong>
          </div>
        </section>

        <section className="overview-metrics" aria-label="Resumo da demonstração">
          <article><strong>{metrics.segmentCount}</strong><span>trechos de 100 m</span></article>
          <article><strong>{queue.metadata.total_count}</strong><span>análises apresentadas</span></article>
          <article><strong>{metrics.awaitingReview}</strong><span>decisões pendentes</span></article>
          <article><strong>{metrics.preparedInspectionOrders}</strong><span>ordens preparadas</span></article>
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
                <p className="eyebrow">Próxima decisão</p>
                <h2>{focus ? `Trecho #${focus.segment_index}` : "Fila concluída"}</h2>
              </div>
              {focus ? <span className="status-pill review">Confiança baixa</span> : null}
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
              <p>Nenhuma recomendação está disponível neste ambiente.</p>
            )}
          </article>

          <aside className="boundary-card" aria-labelledby="boundary-title">
            <p className="eyebrow">Limites atuais</p>
            <h2 id="boundary-title">O que esta demo comprova</h2>
            <ul>
              <li><strong>Comprova</strong><span>Fluxo, rastreabilidade e decisão humana.</span></li>
              <li><strong>Não comprova</strong><span>Altura por satélite ou eixo rodoviário oficial.</span></li>
              <li><strong>Bloqueado</strong><span>Execução real, relatório oficial e treino de modelo.</span></li>
            </ul>
          </aside>
        </section>
      </div>
    </main>
  );
}
