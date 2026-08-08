import Link from "next/link";

import { formatAcquisitionDate } from "../../lib/satellite-observations";
import {
  explanationReasons,
  isRecommendationQueue,
  type RecommendationQueue,
} from "../../lib/recommendations";

export const dynamic = "force-dynamic";

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

function recommendationLabel(value: RecommendationQueue["items"][number]["recommendation"]) {
  if (value === "inspect") return "Inspecionar";
  if (value === "mowing_review") return "Revisar proposta de roçada";
  return "Monitorar";
}

export default async function RecommendationsPage() {
  const queue = await loadRecommendations();
  return (
    <main className="recommendations-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true"><i /></span>
          <div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div>
        </div>
        <nav className="topnav" aria-label="Navegação principal">
          <Link href="/">Corredor</Link>
          <Link aria-current="page" href="/recommendations">Recomendações</Link>
        </nav>
        <div className="update-context"><span>Fluxo</span><strong>somente leitura</strong></div>
      </header>

      <section className="queue-heading">
        <div>
          <p className="eyebrow">Fila gerencial</p>
          <h1>Recomendações para revisão</h1>
          <p className="subtitle">Resultados explicáveis que ainda dependem de política e decisão humana.</p>
        </div>
        <div className="warning-banner" role="status">
          <span className="warning-icon" aria-hidden="true">!</span>
          <div><strong>Nenhum item autoriza trabalho de campo</strong><span>{queue.metadata.warning}</span></div>
        </div>
      </section>

      <section className="queue-summary" aria-label="Resumo da fila">
        <strong>{queue.metadata.result_count}</strong>
        <span>de {queue.metadata.total_count} recomendação(ões) exibida(s)</span>
        {queue.metadata.truncated ? <small>Lista limitada aos {queue.metadata.limit} itens mais recentes.</small> : null}
      </section>

      <section className="recommendation-list" aria-label="Recomendações">
        {queue.items.length === 0 ? (
          <div className="queue-empty"><h2>Fila vazia</h2><p>Nenhuma recomendação exige revisão neste ambiente.</p></div>
        ) : queue.items.map((item) => {
          const reasons = explanationReasons(item.explanation);
          return (
            <article className="recommendation-card" key={item.vegetation_analysis_id}>
              <div className="recommendation-title">
                <div><p className="eyebrow">Trecho #{item.segment_index.toString().padStart(3, "0")} · zona {item.zone_type}</p><h2>{recommendationLabel(item.recommendation)}</h2></div>
                <span className="status-pill review">{item.review_state === "awaiting_review" ? "Aguardando revisão" : "Política pendente"}</span>
              </div>
              <dl className="queue-detail-grid">
                <div><dt>Aquisição</dt><dd>{formatAcquisitionDate(item.acquired_at)}</dd></div>
                <div><dt>Confiança</dt><dd>{item.confidence_band === "low" ? "Baixa" : item.confidence_band}</dd></div>
                <div><dt>Conclusão</dt><dd>{item.conclusion === "inconclusive" ? "Inconclusiva" : "Conclusiva"}</dd></div>
                <div><dt>Revisões</dt><dd>{item.review_count}</dd></div>
              </dl>
              <div className="recommendation-reasons">
                <strong>Explicação</strong>
                {reasons.length ? <ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <p>Sem motivos textuais adicionais.</p>}
              </div>
              <footer>
                <span>Regra {item.rule_version} · processador {item.processor_version}</span>
                <div><strong>Uso em campo: bloqueado</strong><Link href={`/?segment=${item.segment_index}`}>Ver trecho e evidências</Link></div>
              </footer>
            </article>
          );
        })}
      </section>
    </main>
  );
}
