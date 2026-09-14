import { randomUUID } from "node:crypto";

import Link from "next/link";

import { DashboardHeader } from "../../components/dashboard-header";
import { loadDashboardSession } from "../../lib/dashboard-session";
import { formatAcquisitionDate } from "../../lib/satellite-observations";
import {
  explanationReasonLabel,
  explanationReasons,
  isRecommendationQueue,
  recommendationLabel,
  type RecommendationQueue,
  type RecommendationQueueItem,
  zoneLabel,
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

function reviewStateLabel(state: RecommendationQueueItem["review_state"]): string {
  if (state === "awaiting_review") return "Aguardando decisão";
  if (state === "review_recorded_policy_pending") return "Política pendente";
  return "Decisão registrada";
}

function decisionLabel(decision: RecommendationQueueItem["latest_review_decision"]): string {
  if (decision === "accepted") return "Recomendação aceita";
  if (decision === "rejected") return "Recomendação rejeitada";
  if (decision === "adjusted") return "Recomendação ajustada";
  return "Sem decisão";
}

function RecommendationReviewForm({
  csrfToken,
  item,
}: {
  csrfToken: string;
  item: RecommendationQueueItem;
}) {
  return (
    <form
      action={`/api/recommendations/${item.vegetation_analysis_id}/decisions`}
      className="decision-form"
      method="post"
    >
      <input name="csrf_token" type="hidden" value={csrfToken} />
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
        <label htmlFor={`adjustment-${item.vegetation_analysis_id}`}>Ajuste, se necessário</label>
        <select
          id={`adjustment-${item.vegetation_analysis_id}`}
          name="adjusted_recommendation"
        >
          <option value="">Selecione apenas se ajustar</option>
          <option value="monitor">Monitorar</option>
          <option value="inspect">Inspecionar</option>
          <option value="mowing_review">Avaliar roçada</option>
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
        {item.latest_review_id ? "Registrar correção" : "Registrar decisão"}
      </button>
      <small>A decisão fica registrada, mas não autoriza trabalho de campo.</small>
    </form>
  );
}

export default async function RecommendationsPage({ searchParams }: RecommendationsPageProps) {
  const [queue, session, query] = await Promise.all([
    loadRecommendations(),
    loadDashboardSession(),
    searchParams,
  ]);
  const message = operationMessage(query.auth, query.decision, query.order);
  return (
    <main className="recommendations-shell" id="main-content" tabIndex={-1}>
      <DashboardHeader
        active="decisions"
        context={{ label: "Fluxo", value: "somente leitura" }}
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

      <section className="queue-heading">
        <div>
          <p className="eyebrow">Etapa 3 de 5 · decisão humana</p>
          <h1>Decisões pendentes</h1>
          <p className="subtitle">
            Veja o motivo, registre a decisão e preserve a trilha de auditoria.
          </p>
        </div>
        <div className="warning-banner" role="status">
          <span className="warning-icon" aria-hidden="true">!</span>
          <div>
            <strong>Demonstração segura</strong>
            <span>Nenhuma decisão nesta tela libera trabalho de campo.</span>
          </div>
        </div>
      </section>

      {message ? <p className="operation-message" role="status">{message}</p> : null}

      <section className="reviewer-session" aria-label="Sessão de revisão">
        {session ? (
          <>
            <div>
              <strong>{session.user.display_name}</strong>
              <span>Revisor autenticado</span>
            </div>
            <div className="role-list">
              {session.road_roles.length ? session.road_roles.map((role) => (
                <span key={`${role.road_code}-${role.role}`}>
                  {role.road_code} · {role.role}
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
        <span>item(ns) nesta fila</span>
        {queue.metadata.truncated ? <small>Exibindo os {queue.metadata.limit} itens mais recentes.</small> : null}
      </section>

      <section className="recommendation-list" aria-label="Recomendações">
        {queue.items.length === 0 ? (
          <div className="queue-empty"><h2>Fila vazia</h2><p>Nenhuma recomendação exige revisão neste ambiente.</p></div>
        ) : queue.items.map((item) => {
          const reasons = explanationReasons(item.explanation);
          const isAwaitingReview = item.review_state === "awaiting_review";
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
            <article
              className={`recommendation-card ${isAwaitingReview ? "is-pending" : "is-reviewed"}`}
              key={item.vegetation_analysis_id}
            >
              <div className="recommendation-title">
                <div>
                  <p className="eyebrow">
                    {item.road_code} · trecho #{item.segment_index.toString().padStart(3, "0")}
                  </p>
                  <h2>{recommendationLabel(item.recommendation)}</h2>
                </div>
                <span className="status-pill review">
                  {reviewStateLabel(item.review_state)}
                </span>
              </div>
              <dl className="decision-overview-grid">
                <div><dt>Área</dt><dd>{zoneLabel(item.zone_type)}</dd></div>
                <div>
                  <dt>Confiança</dt>
                  <dd>{item.confidence_band === "low" ? "Baixa" : item.confidence_band}</dd>
                </div>
                <div><dt>Próximo passo</dt><dd>Revisão humana</dd></div>
              </dl>
              <div className="recommendation-reasons">
                <strong>Por que o sistema sugeriu isso?</strong>
                {reasons.length ? (
                  <ul>
                    {reasons.slice(0, 3).map((reason) => (
                      <li key={reason}>{explanationReasonLabel(reason)}</li>
                    ))}
                  </ul>
                ) : <p>Sem motivos textuais adicionais.</p>}
              </div>
              {!isAwaitingReview ? (
                <div className="recorded-decision">
                  <span>Última decisão</span>
                  <strong>{decisionLabel(item.latest_review_decision)}</strong>
                  {effectiveAction ? <small>Ação resultante: {recommendationLabel(effectiveAction)}</small> : null}
                </div>
              ) : null}
              {session && canReview && isAwaitingReview ? (
                <RecommendationReviewForm csrfToken={session.csrfToken} item={item} />
              ) : session && canReview ? (
                <details className="progressive-details correction-details">
                  <summary>Corrigir decisão registrada</summary>
                  <RecommendationReviewForm csrfToken={session.csrfToken} item={item} />
                </details>
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
                  <small>Três pontos estimados · execução em campo bloqueada.</small>
                </div>
              ) : null}
              <details className="progressive-details audit-details">
                <summary>Detalhes técnicos e auditoria</summary>
                <dl className="queue-detail-grid">
                  <div><dt>Aquisição</dt><dd>{formatAcquisitionDate(item.acquired_at)}</dd></div>
                  <div>
                    <dt>Conclusão</dt>
                    <dd>{item.conclusion === "inconclusive" ? "Inconclusiva" : "Conclusiva"}</dd>
                  </div>
                  <div><dt>Revisões</dt><dd>{item.review_count}</dd></div>
                  <div><dt>Regra</dt><dd>{item.rule_version}</dd></div>
                  <div><dt>Processador</dt><dd>{item.processor_version}</dd></div>
                  {item.latest_review_policy_version ? (
                    <div>
                      <dt>Política</dt>
                      <dd>
                        {item.latest_review_policy_version} ({item.latest_review_policy_data_status})
                      </dd>
                    </div>
                  ) : null}
                  {item.prepared_inspection_order_id ? (
                    <div><dt>ID da ordem</dt><dd>{item.prepared_inspection_order_id}</dd></div>
                  ) : null}
                </dl>
              </details>
              <footer>
                <strong>Uso em campo: bloqueado</strong>
                <Link href={`/corridor?segment=${item.segment_index}`}>Ver evidências no mapa</Link>
              </footer>
            </article>
          );
        })}
      </section>
    </main>
  );
}
