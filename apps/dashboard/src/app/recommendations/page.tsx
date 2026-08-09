import { randomUUID } from "node:crypto";

import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import { formatAcquisitionDate } from "../../lib/satellite-observations";
import {
  explanationReasons,
  isRecommendationQueue,
  type RecommendationQueue,
} from "../../lib/recommendations";

export const dynamic = "force-dynamic";

interface RecommendationsPageProps {
  searchParams: Promise<{ auth?: string; decision?: string; order?: string }>;
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

function recommendationLabel(value: RecommendationQueue["items"][number]["recommendation"]) {
  if (value === "inspect") return "Inspecionar";
  if (value === "mowing_review") return "Revisar proposta de roçada";
  return "Monitorar";
}

function operationMessage(
  auth: string | undefined,
  decision: string | undefined,
  order: string | undefined,
): string | null {
  if (auth === "signed-in") return "Sessão autenticada. As decisões serão vinculadas ao seu usuário.";
  if (decision === "recorded") return "Decisão registrada na trilha de auditoria.";
  if (decision === "forbidden") return "Seu usuário não possui o papel exigido para esta rodovia.";
  if (decision === "conflict") return "A operação já foi usada com dados diferentes. Atualize a página.";
  if (decision === "missing") return "A recomendação não foi encontrada.";
  if (decision === "invalid") return "A decisão está incompleta ou inválida.";
  if (decision === "service-unavailable") return "Não foi possível registrar a decisão agora.";
  if (order === "prepared") return "Ordem de inspeção preparada com três pontos não operacionais.";
  if (order === "forbidden") return "Seu usuário não pode preparar uma ordem para esta rodovia.";
  if (order === "missing-review") return "A decisão de origem não foi encontrada.";
  if (order === "conflict") return "A decisão mudou ou já possui uma ordem preparada. Atualize a página.";
  if (order === "invalid") return "Revise a justificativa da ordem de inspeção.";
  if (order === "service-unavailable") return "Não foi possível preparar a ordem agora.";
  return null;
}

export default async function RecommendationsPage({ searchParams }: RecommendationsPageProps) {
  const [queue, session, query] = await Promise.all([
    loadRecommendations(),
    loadDashboardSession(),
    searchParams,
  ]);
  const message = operationMessage(query.auth, query.decision, query.order);
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
        {session ? (
          <div className="session-context">
            <span>{session.user.display_name}</span>
            <form action="/api/auth/logout" method="post">
              <input name="csrf_token" type="hidden" value={session.csrfToken} />
              <button type="submit">Sair</button>
            </form>
          </div>
        ) : (
          <div className="update-context"><span>Fluxo</span><strong>somente leitura</strong></div>
        )}
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

      {message ? <p className="operation-message" role="status">{message}</p> : null}

      <section className="reviewer-session" aria-label="Sessão de revisão">
        {session ? (
          <>
            <div>
              <strong>Revisor autenticado</strong>
              <span>{session.user.email}</span>
            </div>
            <div className="role-list">
              {session.road_roles.length ? session.road_roles.map((role) => (
                <span key={`${role.road_code}-${role.role}`}>
                  {role.road_code} · {role.role} · {role.data_status}
                </span>
              )) : <span>Sem papel de revisão atribuído</span>}
            </div>
          </>
        ) : (
          <>
            <div><strong>Fila em modo somente leitura</strong><span>Entre para registrar uma decisão humana.</span></div>
            <Link className="primary-button" href="/login">Entrar</Link>
          </>
        )}
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
          const canReview = session?.road_roles.some(
            (role) => role.road_code === item.road_code && role.data_status !== "simulated",
          ) ?? false;
          const effectiveAction = item.latest_review_decision === "adjusted"
            ? item.latest_review_adjusted_recommendation
            : item.latest_review_decision === "accepted"
              ? item.recommendation
              : null;
          const canPrepareInspectionOrder = Boolean(
            session &&
            canReview &&
            item.latest_review_id &&
            item.review_state === "review_recorded_no_work_authorization" &&
            effectiveAction === "inspect" &&
            !item.prepared_inspection_order_id,
          );
          return (
            <article className="recommendation-card" key={item.vegetation_analysis_id}>
              <div className="recommendation-title">
                <div><p className="eyebrow">Trecho #{item.segment_index.toString().padStart(3, "0")} · zona {item.zone_type}</p><h2>{recommendationLabel(item.recommendation)}</h2></div>
                <span className="status-pill review">
                  {item.review_state === "awaiting_review"
                    ? "Aguardando revisão"
                    : item.review_state === "review_recorded_policy_pending"
                      ? "Revisão legada — política pendente"
                      : "Revisão registrada — sem autorização de campo"}
                </span>
              </div>
              <dl className="queue-detail-grid">
                <div><dt>Aquisição</dt><dd>{formatAcquisitionDate(item.acquired_at)}</dd></div>
                <div><dt>Confiança</dt><dd>{item.confidence_band === "low" ? "Baixa" : item.confidence_band}</dd></div>
                <div><dt>Conclusão</dt><dd>{item.conclusion === "inconclusive" ? "Inconclusiva" : "Conclusiva"}</dd></div>
                <div><dt>Revisões</dt><dd>{item.review_count}</dd></div>
                {item.latest_review_policy_version ? (
                  <div>
                    <dt>Política da última revisão</dt>
                    <dd>{item.latest_review_policy_version} ({item.latest_review_policy_data_status})</dd>
                  </div>
                ) : null}
              </dl>
              <div className="recommendation-reasons">
                <strong>Explicação</strong>
                {reasons.length ? <ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <p>Sem motivos textuais adicionais.</p>}
              </div>
              {session && canReview ? (
                <form
                  action={`/api/recommendations/${item.vegetation_analysis_id}/decisions`}
                  className="decision-form"
                  method="post"
                >
                  <input name="csrf_token" type="hidden" value={session.csrfToken} />
                  <input name="idempotency_key" type="hidden" value={randomUUID()} />
                  {item.latest_review_id ? (
                    <input name="supersedes_review_id" type="hidden" value={item.latest_review_id} />
                  ) : null}
                  <div>
                    <label htmlFor={`decision-${item.vegetation_analysis_id}`}>Decisão</label>
                    <select id={`decision-${item.vegetation_analysis_id}`} name="decision">
                      <option value="accepted">Aceitar recomendação</option>
                      <option value="rejected">Rejeitar recomendação</option>
                      <option value="adjusted">Ajustar recomendação</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor={`adjustment-${item.vegetation_analysis_id}`}>Ajuste, se aplicável</label>
                    <select id={`adjustment-${item.vegetation_analysis_id}`} name="adjusted_recommendation">
                      <option value="">Selecione para uma decisão ajustada</option>
                      <option value="monitor">Monitorar</option>
                      <option value="inspect">Inspecionar</option>
                      <option value="mowing_review">Revisar proposta de roçada</option>
                    </select>
                  </div>
                  <div className="decision-rationale">
                    <label htmlFor={`rationale-${item.vegetation_analysis_id}`}>Justificativa</label>
                    <textarea
                      id={`rationale-${item.vegetation_analysis_id}`}
                      maxLength={2000}
                      name="rationale"
                      placeholder="Obrigatória ao rejeitar ou ajustar"
                      rows={3}
                    />
                  </div>
                  <button className="primary-button" type="submit">
                    {item.latest_review_id ? "Registrar correção auditável" : "Registrar decisão"}
                  </button>
                  <small>Esta ação registra revisão; não cria nem autoriza ordem de campo.</small>
                </form>
              ) : session ? (
                <p className="role-warning">Seu usuário não possui papel elegível de revisão para {item.road_code}.</p>
              ) : null}
              {canPrepareInspectionOrder && item.latest_review_id ? (
                <form action="/api/work-orders" className="inspection-order-form" method="post">
                  <input name="csrf_token" type="hidden" value={session?.csrfToken} />
                  <input name="idempotency_key" type="hidden" value={randomUUID()} />
                  <input name="source_review_id" type="hidden" value={item.latest_review_id} />
                  <div>
                    <label htmlFor={`order-rationale-${item.vegetation_analysis_id}`}>
                      Justificativa do planejamento
                    </label>
                    <textarea
                      id={`order-rationale-${item.vegetation_analysis_id}`}
                      maxLength={2000}
                      name="planning_rationale"
                      placeholder="Explique por que a inspeção deve ser preparada"
                      required
                      rows={3}
                    />
                  </div>
                  <button className="primary-button" type="submit">Preparar ordem de inspeção</button>
                  <small>
                    Gera três pontos estimados sobre o eixo. Não libera execução nem deslocamento de equipe.
                  </small>
                </form>
              ) : item.prepared_inspection_order_id ? (
                <div className="prepared-order-state">
                  <strong>Ordem de inspeção preparada</strong>
                  <span>{item.prepared_inspection_order_id}</span>
                  <small>Três pontos estimados; execução em campo bloqueada.</small>
                </div>
              ) : null}
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
