import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";
import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  isMowingPostServiceExceptionCollection,
  type MowingPostServiceExceptionCollection,
} from "../../lib/mowing-post-service-exceptions";
import {
  mowingPostServiceExceptionEffectiveDecision,
  mowingPostServiceExceptionHeadline,
  mowingPostServiceExceptionReviewStatus,
} from "../../lib/mowing-post-service-exception-presenter";
import {
  isMowingPostServiceSummaryCollection,
  type MowingPostServiceSummaryCollection,
} from "../../lib/mowing-post-service-summaries";
import { SESSION_COOKIE_NAME } from "../../lib/session-security";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    export?: string;
    mowing_exception?: string;
    exception_review?: string;
  }>;
}

async function loadSummaries(): Promise<MowingPostServiceSummaryCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const response = await fetch(
    `${process.env.INTERNAL_API_URL ?? "http://localhost:8000"}/v1/prepared-mowing-post-service-summaries?limit=50`,
    { cache: "no-store", headers: { Authorization: `Bearer ${token}` } },
  );
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(`Mowing post-service summaries returned HTTP ${response.status}`);
  }
  const payload: unknown = await response.json();
  if (!isMowingPostServiceSummaryCollection(payload)) {
    throw new Error("Mowing post-service summary safety contract is invalid");
  }
  return payload;
}

async function loadExceptions(): Promise<MowingPostServiceExceptionCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const response = await fetch(
    `${process.env.INTERNAL_API_URL ?? "http://localhost:8000"}/v1/prepared-mowing-post-service-exceptions?limit=50`,
    { cache: "no-store", headers: { Authorization: `Bearer ${token}` } },
  );
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(`Mowing post-service exceptions returned HTTP ${response.status}`);
  }
  const payload: unknown = await response.json();
  if (!isMowingPostServiceExceptionCollection(payload)) {
    throw new Error("Mowing post-service exception safety contract is invalid");
  }
  return payload;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

function cm(value: string | number): string {
  return `${Number(value).toFixed(2)} cm`;
}

function exportMessage(status?: string): string | null {
  if (status === "missing") {
    return "O resumo pós-serviço simulado não foi encontrado ou não está acessível.";
  }
  if (status === "conflict") {
    return "A chave da exportação entrou em conflito com outra solicitação.";
  }
  if (status === "invalid") return "Informe um propósito válido para exportar o resumo.";
  if (status === "unsafe-response") {
    return "A exportação foi bloqueada porque o CSV não confirmou os rótulos simulados.";
  }
  if (status === "service-unavailable") {
    return "O serviço de exportação não está disponível agora.";
  }
  return null;
}

function exceptionReviewMessage(status?: string): string | null {
  if (status === "recorded") {
    return "Revisão humana da exceção registrada na trilha append-only.";
  }
  if (status === "forbidden") {
    return "Seu usuário não pode revisar esta exceção nesta rodovia.";
  }
  if (status === "missing") return "A exceção pós-serviço simulada não foi encontrada.";
  if (status === "conflict") {
    return "A chave de repetição ou a revisão efetiva entrou em conflito.";
  }
  if (status === "invalid") {
    return "A decisão da exceção está incompleta ou inconsistente.";
  }
  if (status === "service-unavailable") {
    return "O serviço de revisão da exceção não está disponível agora.";
  }
  return null;
}

function mowingExceptionMessage(status?: string): string | null {
  if (status === "created") {
    return "Exceção pós-serviço simulada registrada para revisão humana.";
  }
  if (status === "forbidden") {
    return "Seu usuário não pode avaliar exceção pós-serviço nesta rodovia.";
  }
  if (status === "missing") return "O resumo pós-serviço simulado não foi encontrado.";
  if (status === "conflict") return "A exceção já existe ou a chave entrou em conflito.";
  if (status === "invalid") return "A justificativa da exceção pós-serviço é inválida.";
  if (status === "service-unavailable") {
    return "O serviço de exceções pós-serviço não está disponível agora.";
  }
  return null;
}

export default async function MowingPostServiceSummariesPage({ searchParams }: PageProps) {
  const [session, summaries, exceptions, query] = await Promise.all([
    loadDashboardSession(),
    loadSummaries(),
    loadExceptions(),
    searchParams,
  ]);
  const operationMessage =
    mowingExceptionMessage(query.mowing_exception) ??
    exceptionReviewMessage(query.exception_review) ??
    exportMessage(query.export);
  const exceptionBySummary = new Map(
    exceptions?.items.map((item) => [item.summary_id, item]) ?? [],
  );

  return (
    <main className="recommendations-shell">
      <header className="topbar">
        <div className="brand-block">
          <span aria-hidden="true" className="brand-mark"><i /></span>
          <div>
            <strong>ZENIT</strong>
            <small>Vegetação rodoviária</small>
          </div>
        </div>
        <nav aria-label="Navegação principal" className="topnav">
          <Link href="/">Corredor</Link>
          <Link href="/recommendations">Recomendações</Link>
          <Link href="/photo-reviews">Fotos de inspeção</Link>
          <Link href="/mowing-photo-reviews">Fotos pós-serviço</Link>
          <Link aria-current="page" href="/mowing-post-service-summaries">
            Resumos pós-serviço
          </Link>
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

      <section className="queue-heading">
        <div>
          <p className="eyebrow">Agregação · pós-serviço simulado</p>
          <h1>Resumos do ensaio de roçada</h1>
          <p className="subtitle">
            Consulta somente leitura dos agregados gerados após três medições digitadas e
            três revisões visuais aceitas.
          </p>
        </div>
        <div className="warning-banner" role="status">
          <span aria-hidden="true" className="warning-icon">!</span>
          <div>
            <strong>Não é conclusão operacional</strong>
            <span>
              O resumo não comprova roçada, eficácia, campo, treinamento ou relatório oficial.
            </span>
          </div>
        </div>
      </section>

      {operationMessage ? <p className="operation-message" role="status">{operationMessage}</p> : null}

      {!session || !summaries ? (
        <section className="reviewer-session">
          <div>
            <strong>Sessão necessária</strong>
            <span>Entre para acessar resumos pós-serviço da sua rodovia.</span>
          </div>
          <Link className="primary-button" href="/login">Entrar</Link>
        </section>
      ) : (
        <>
          <section className="reviewer-session">
            <div>
              <strong>{session.user.display_name}</strong>
              <span>{session.user.email}</span>
            </div>
            <div className="role-list">
              {session.road_roles.map((role) => (
                <span key={`${role.road_code}-${role.role}`}>
                  {role.road_code} · {role.role}
                </span>
              ))}
            </div>
          </section>

          <section className="queue-summary">
            <strong>{summaries.result_count}</strong>
            <span>resumo(s) pós-serviço acessível(is)</span>
            {summaries.truncated ? <small>Lista limitada a {summaries.limit} itens.</small> : null}
          </section>

          <p className="quality-note">
            <span>i</span>
            <span><strong>Escopo seguro</strong> {summaries.warning}</span>
          </p>

          <section aria-label="Resumos pós-serviço simulados" className="prepared-summary-grid">
            {summaries.items.length === 0 ? (
              <div className="queue-empty">
                <h2>Nenhum resumo</h2>
                <p>Não há resumo pós-serviço simulado disponível para seu papel.</p>
              </div>
            ) : summaries.items.map((item) => {
              const exception = exceptionBySummary.get(item.summary_id);
              return (
                <article className="prepared-summary-card" key={item.summary_id}>
                  <div className="prepared-summary-heading">
                    <div>
                      <p className="eyebrow">Ordem {item.mowing_order_id}</p>
                      <h2>Resumo pós-serviço</h2>
                    </div>
                    <span className="status-pill simulated">Simulado</span>
                  </div>

                  <dl className="summary-metrics">
                    <div>
                      <dt>Mínima</dt>
                      <dd>{cm(item.minimum_height_cm)}</dd>
                    </div>
                    <div>
                      <dt>Média</dt>
                      <dd>{cm(item.mean_height_cm)}</dd>
                    </div>
                    <div>
                      <dt>Máxima</dt>
                      <dd>{cm(item.maximum_height_cm)}</dd>
                    </div>
                  </dl>

                  <div className="summary-classes">
                    <span>N1 {item.n1_count}</span>
                    <span>N2 {item.n2_count}</span>
                    <span>N3 {item.n3_count}</span>
                  </div>

                  <p className="summary-rationale">{item.generation_rationale}</p>
                  <small>
                    {item.summary_policy_version} · gerado {formatDate(item.generated_at)} ·{" "}
                    {item.measurement_count} medições · {item.accepted_photo_review_count} fotos
                    aceitas
                  </small>

                  {exception ? (
                    <>
                      <div className="post-inspection-proposal">
                        <div>
                          <strong>{mowingPostServiceExceptionHeadline(exception)}</strong>
                          <span>
                            Máxima {cm(exception.maximum_height_cm)} · limiar{" "}
                            {cm(exception.applicable_threshold_cm)}
                          </span>
                        </div>
                        <span className="status-pill review">
                          {mowingPostServiceExceptionReviewStatus(exception)}
                        </span>
                        <small>
                          Exceção simulada; não conclui roçada, não atualiza mapa e não autoriza
                          campo.
                        </small>
                        {mowingPostServiceExceptionEffectiveDecision(exception) ? (
                          <small>
                            Decisão efetiva: {mowingPostServiceExceptionEffectiveDecision(exception)} ·{" "}
                            {formatDate(exception.latest_reviewed_at ?? exception.created_at)}
                          </small>
                        ) : null}
                        {exception.latest_review_rationale ? (
                          <p className="summary-rationale">{exception.latest_review_rationale}</p>
                        ) : null}
                      </div>

                      <form
                        action={`/api/prepared-mowing-post-service-exceptions/${exception.exception_id}/decisions`}
                        className="decision-form"
                        method="post"
                      >
                        <input name="csrf_token" type="hidden" value={session.csrfToken} />
                        <input name="idempotency_key" type="hidden" value={randomUUID()} />
                        {exception.latest_review_id ? (
                          <input
                            name="supersedes_review_id"
                            type="hidden"
                            value={exception.latest_review_id}
                          />
                        ) : null}
                        <div>
                          <label htmlFor={`mowing-exception-decision-${exception.exception_id}`}>
                            Decisão
                          </label>
                          <select
                            defaultValue="accepted"
                            id={`mowing-exception-decision-${exception.exception_id}`}
                            name="decision"
                          >
                            <option value="accepted">Aceitar</option>
                            <option value="rejected">Rejeitar</option>
                            <option value="adjusted">Ajustar</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor={`mowing-exception-adjusted-${exception.exception_id}`}>
                            Ajuste
                          </label>
                          <select
                            defaultValue=""
                            id={`mowing-exception-adjusted-${exception.exception_id}`}
                            name="adjusted_recommendation"
                          >
                            <option value="">Selecione ao ajustar</option>
                            <option value="monitor">Monitoramento</option>
                            <option value="inspect_follow_up">Inspeção de seguimento</option>
                          </select>
                        </div>
                        <div className="decision-rationale">
                          <label htmlFor={`mowing-exception-rationale-${exception.exception_id}`}>
                            Justificativa
                          </label>
                          <textarea
                            defaultValue={
                              exception.latest_review_decision === "adjusted"
                                ? exception.latest_review_rationale ?? ""
                                : ""
                            }
                            id={`mowing-exception-rationale-${exception.exception_id}`}
                            maxLength={2000}
                            name="rationale"
                            placeholder="Obrigatória para rejeição ou ajuste"
                            rows={3}
                          />
                        </div>
                        <button className="primary-button" type="submit">
                          {exception.latest_review_id ? "Registrar correção" : "Registrar revisão"}
                        </button>
                        <small>
                          O ajuste continua limitado a monitoramento ou inspeção de seguimento, sem
                          autorizar campo.
                        </small>
                      </form>
                    </>
                  ) : (
                    <form
                      action={`/api/prepared-mowing-post-service-summaries/${item.summary_id}/exceptions`}
                      className="prepared-summary-form"
                      method="post"
                    >
                      <input name="csrf_token" type="hidden" value={session.csrfToken} />
                      <input name="idempotency_key" type="hidden" value={randomUUID()} />
                      <label htmlFor={`mowing-exception-rationale-${item.summary_id}`}>
                        Justificativa da avaliação de exceção
                      </label>
                      <textarea
                        defaultValue="Aplicar limiar preparado ao resumo pós-serviço simulado"
                        id={`mowing-exception-rationale-${item.summary_id}`}
                        maxLength={2000}
                        name="creation_rationale"
                        required
                        rows={3}
                      />
                      <button className="primary-button" type="submit">
                        Avaliar exceção pós-serviço
                      </button>
                      <small>
                        Se a máxima exceder o limiar, gera somente indicação de inspeção de
                        seguimento com revisão humana.
                      </small>
                    </form>
                  )}

                  <form
                    action={`/api/prepared-mowing-post-service-summaries/${item.summary_id}/exports`}
                    className="summary-export-form"
                    method="post"
                  >
                    <input name="csrf_token" type="hidden" value={session.csrfToken} />
                    <input name="idempotency_key" type="hidden" value={randomUUID()} />
                    <label htmlFor={`mowing-export-purpose-${item.summary_id}`}>
                      Propósito da exportação
                    </label>
                    <input
                      defaultValue="Compartilhar pós-serviço simulado para revisão"
                      id={`mowing-export-purpose-${item.summary_id}`}
                      maxLength={2000}
                      name="export_purpose"
                      required
                    />
                    <button className="secondary-button" type="submit">
                      Baixar CSV simulado
                    </button>
                    <small>
                      O download gera auditoria e mantém bloqueio de relatório oficial, treino e
                      autorização de campo.
                    </small>
                  </form>
                </article>
              );
            })}
          </section>
        </>
      )}
    </main>
  );
}
