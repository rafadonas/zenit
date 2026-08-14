import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";
import Image from "next/image";
import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  isPreparedMowingRehearsalCollection,
  type MowingRehearsalState,
  type PreparedMowingRehearsalCollection,
} from "../../lib/mowing-rehearsals";
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
import { isPhotoReviewQueue, type PhotoReviewQueue } from "../../lib/photo-reviews";
import {
  isPreparedProposalCollection, type PreparedPostInspectionProposal,
  type PreparedProposalCollection,
} from "../../lib/post-inspection-proposals";
import {
  isPreparedSummaryCollection, type PreparedInspectionSummary,
  type PreparedSummaryCollection,
} from "../../lib/prepared-summaries";
import { SESSION_COOKIE_NAME } from "../../lib/session-security";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    review?: string; summary?: string; export?: string; proposal?: string;
    proposal_review?: string; mowing_order?: string; resource_plan?: string;
    readiness?: string; planning_approval?: string; mowing_summary?: string;
    mowing_exception?: string;
  }>;
}

async function loadQueue(): Promise<PhotoReviewQueue | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/photo-review-queue?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Photo review queue returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isPhotoReviewQueue(payload)) throw new Error("Photo review queue safety contract is invalid");
  return payload;
}

async function loadSummaries(): Promise<PreparedSummaryCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/prepared-inspection-summaries?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Prepared summary list returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isPreparedSummaryCollection(payload)) {
    throw new Error("Prepared summary safety contract is invalid");
  }
  return payload;
}

async function loadProposals(): Promise<PreparedProposalCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/prepared-post-inspection-proposals?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Prepared proposal list returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isPreparedProposalCollection(payload)) {
    throw new Error("Prepared proposal safety contract is invalid");
  }
  return payload;
}

async function loadMowingRehearsals(): Promise<PreparedMowingRehearsalCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/prepared-mowing-rehearsals?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Prepared mowing rehearsal list returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isPreparedMowingRehearsalCollection(payload)) {
    throw new Error("Prepared mowing rehearsal safety contract is invalid");
  }
  return payload;
}

async function loadMowingSummaries(): Promise<MowingPostServiceSummaryCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/prepared-mowing-post-service-summaries?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Prepared mowing summary list returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isMowingPostServiceSummaryCollection(payload)) {
    throw new Error("Prepared mowing summary safety contract is invalid");
  }
  return payload;
}

async function loadMowingExceptions(): Promise<MowingPostServiceExceptionCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/v1/prepared-mowing-post-service-exceptions?limit=50`, {
    cache: "no-store", headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Prepared mowing exception list returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isMowingPostServiceExceptionCollection(payload)) {
    throw new Error("Prepared mowing exception safety contract is invalid");
  }
  return payload;
}

function message(
  review?: string, summary?: string, exportStatus?: string, proposal?: string,
  proposalReview?: string, mowingOrder?: string, resourcePlan?: string,
  readiness?: string, planningApproval?: string, mowingSummary?: string,
  mowingException?: string,
): string | null {
  if (mowingException === "created") return "Exceção pós-serviço simulada registrada para revisão humana.";
  if (mowingException === "forbidden") return "Seu usuário não pode avaliar exceção pós-serviço nesta rodovia.";
  if (mowingException === "missing") return "O resumo pós-serviço simulado não foi encontrado.";
  if (mowingException === "conflict") return "A exceção já existe ou a chave entrou em conflito.";
  if (mowingException === "invalid") return "A justificativa da exceção pós-serviço é inválida.";
  if (mowingException === "service-unavailable") return "O serviço de exceções pós-serviço não está disponível agora.";
  if (mowingSummary === "generated") return "Resumo pós-serviço simulado gerado; continua sem conclusão operacional.";
  if (mowingSummary === "forbidden") return "Seu usuário não pode gerar resumo pós-serviço para esta rodovia.";
  if (mowingSummary === "missing") return "A ordem de roçada preparada não foi encontrada.";
  if (mowingSummary === "conflict") return "O resumo pós-serviço já existe, a evidência está incompleta ou a chave entrou em conflito.";
  if (mowingSummary === "invalid") return "A justificativa do resumo pós-serviço é inválida.";
  if (mowingSummary === "service-unavailable") return "O serviço de resumo pós-serviço não está disponível agora.";
  if (planningApproval === "recorded") return "Decisão sobre o planejamento registrada; aprovação operacional continua não satisfeita.";
  if (planningApproval === "forbidden") return "Seu usuário não pode decidir este planejamento.";
  if (planningApproval === "missing") return "A ordem de roçada preparada não foi encontrada.";
  if (planningApproval === "conflict") return "A avaliação mudou, não permite aprovação ou a correção entrou em conflito.";
  if (planningApproval === "invalid") return "Informe uma decisão e justificativa válidas.";
  if (planningApproval === "service-unavailable") return "O serviço de decisão não está disponível agora.";
  if (readiness === "recorded") return "Avaliação manual de clima e segurança registrada; validação operacional continua pendente.";
  if (readiness === "forbidden") return "Seu usuário não pode avaliar esta ordem.";
  if (readiness === "missing") return "A ordem de roçada preparada não foi encontrada.";
  if (readiness === "conflict") return "A ordem ou o plano de recursos mudou, ou a correção entrou em conflito.";
  if (readiness === "invalid") return "Preencha resultados, fontes e justificativa da avaliação.";
  if (readiness === "service-unavailable") return "O serviço de avaliação não está disponível agora.";
  if (resourcePlan === "recorded") return "Referências candidatas de equipe e equipamento registradas, ainda não atribuídas.";
  if (resourcePlan === "forbidden") return "Seu usuário não pode planejar recursos para esta rodovia.";
  if (resourcePlan === "missing") return "A ordem de roçada preparada não foi encontrada.";
  if (resourcePlan === "conflict") return "A ordem ficou obsoleta, a correção não substitui o plano efetivo ou a chave entrou em conflito.";
  if (resourcePlan === "invalid") return "Informe referências candidatas e uma justificativa válidas.";
  if (resourcePlan === "service-unavailable") return "O serviço de planejamento de recursos não está disponível agora.";
  if (mowingOrder === "created") return "Ordem de roçada preparada para planejamento, sem autorização de execução.";
  if (mowingOrder === "forbidden") return "Seu usuário não pode preparar ordem de roçada para esta rodovia.";
  if (mowingOrder === "missing") return "A revisão humana efetiva não foi encontrada.";
  if (mowingOrder === "conflict") return "A revisão não indica roçada, já possui ordem ou a chave entrou em conflito.";
  if (mowingOrder === "invalid") return "A solicitação da ordem preparada está incompleta.";
  if (mowingOrder === "service-unavailable") return "O serviço de ordens preparadas não está disponível agora.";
  if (proposalReview === "recorded") return "Decisão humana sobre a proposta registrada na trilha append-only.";
  if (proposalReview === "forbidden") return "Seu usuário não pode revisar esta proposta.";
  if (proposalReview === "missing") return "A proposta preparada não foi encontrada.";
  if (proposalReview === "conflict") return "A correção não substitui a revisão efetiva ou a chave entrou em conflito.";
  if (proposalReview === "invalid") return "A decisão sobre a proposta está incompleta ou inválida.";
  if (proposalReview === "service-unavailable") return "O serviço de decisões não está disponível agora.";
  if (proposal === "created") return "Proposta pós-inspeção preparada; decisão humana ainda obrigatória.";
  if (proposal === "forbidden") return "Seu usuário não pode criar proposta para esta rodovia.";
  if (proposal === "missing") return "O resumo preparado não foi encontrado.";
  if (proposal === "conflict") return "A proposta já existe ou a chave entrou em conflito.";
  if (proposal === "invalid") return "A justificativa da proposta é inválida.";
  if (proposal === "service-unavailable") return "O serviço de propostas não está disponível agora.";
  if (exportStatus === "missing") return "O resumo preparado não foi encontrado ou não está acessível.";
  if (exportStatus === "conflict") return "A chave da exportação entrou em conflito com outra solicitação.";
  if (exportStatus === "invalid") return "Informe um propósito válido para exportar o resumo.";
  if (exportStatus === "unsafe-response") return "A exportação foi bloqueada porque o arquivo não confirmou todos os rótulos de segurança.";
  if (exportStatus === "service-unavailable") return "O serviço de exportação não está disponível agora.";
  if (summary === "generated") return "Resumo preparado gerado e registrado de forma imutável.";
  if (summary === "forbidden") return "Seu usuário não pode gerar resumo para esta rodovia.";
  if (summary === "missing") return "A ordem preparada não foi encontrada.";
  if (summary === "conflict") return "O resumo já existe, a evidência está incompleta ou a chave entrou em conflito.";
  if (summary === "invalid") return "A solicitação do resumo está incompleta ou inconsistente.";
  if (summary === "service-unavailable") return "O serviço de resumos não está disponível agora.";
  if (review === "recorded") return "Revisão humana registrada na trilha append-only.";
  if (review === "forbidden") return "Seu usuário não pode revisar esta foto.";
  if (review === "missing") return "A foto preparada não foi encontrada.";
  if (review === "conflict") return "A chave de repetição ou revisão anterior entrou em conflito.";
  if (review === "invalid") return "A revisão está incompleta ou inconsistente.";
  if (review === "service-unavailable") return "O serviço de revisão não está disponível agora.";
  return null;
}

function isAccepted(item: PhotoReviewQueue["items"][number]): boolean {
  return item.latest_decision === "accepted" && item.latest_quality_status === "accepted" &&
    item.latest_ruler_status === "visible";
}

function formatHeight(value: string | number): string {
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

function rehearsalStateLabel(state: MowingRehearsalState): string {
  return {
    not_started: "Não iniciado",
    confirmed: "Confirmado",
    in_progress: "Em andamento",
    paused: "Pausado",
    finished: "Ensaio finalizado",
  }[state];
}

function rehearsalOperationLabel(operation: string): string {
  return {
    confirm: "Confirmação",
    start: "Início simulado",
    pause: "Pausa",
    resume: "Retomada",
    finish: "Encerramento do ensaio",
  }[operation] ?? operation;
}

function formatRehearsalTime(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short", timeStyle: "medium", timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

function formatRecordedSpan(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return minutes === 0 ? `${remainder}s` : `${minutes}min ${remainder}s`;
}

export default async function PhotoReviewsPage({ searchParams }: PageProps) {
  const [
    session, queue, summaries, proposals, rehearsals, mowingSummaries, mowingExceptions, query,
  ] = await Promise.all([
    loadDashboardSession(), loadQueue(), loadSummaries(), loadProposals(),
    loadMowingRehearsals(), loadMowingSummaries(), loadMowingExceptions(), searchParams,
  ]);
  const operationMessage = message(
    query.review, query.summary, query.export, query.proposal, query.proposal_review,
    query.mowing_order, query.resource_plan, query.readiness, query.planning_approval,
    query.mowing_summary, query.mowing_exception,
  );
  const summaryByOrder = new Map<string, PreparedInspectionSummary>(
    summaries?.items.map((summary) => [summary.work_order_id, summary]) ?? [],
  );
  const orderGroups = new Map<string, PhotoReviewQueue["items"]>();
  const proposalBySummary = new Map<string, PreparedPostInspectionProposal>(
    proposals?.items.map((proposal) => [proposal.summary_id, proposal]) ?? [],
  );
  const rehearsalByMowingOrder = new Map(
    rehearsals?.items.map((rehearsal) => [rehearsal.mowing_order_id, rehearsal]) ?? [],
  );
  const mowingSummaryByOrder = new Map(
    mowingSummaries?.items.map((summary) => [summary.mowing_order_id, summary]) ?? [],
  );
  const mowingExceptionBySummary = new Map(
    mowingExceptions?.items.map((item) => [item.summary_id, item]) ?? [],
  );
  for (const item of queue?.items ?? []) {
    const group = orderGroups.get(item.work_order_id) ?? [];
    group.push(item);
    orderGroups.set(item.work_order_id, group);
  }
  return <main className="recommendations-shell">
    <header className="topbar">
      <div className="brand-block"><span className="brand-mark" aria-hidden="true"><i /></span><div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div></div>
      <nav className="topnav" aria-label="Navegação principal"><Link href="/">Corredor</Link><Link href="/recommendations">Recomendações</Link><Link aria-current="page" href="/photo-reviews">Fotos de inspeção</Link><Link href="/mowing-photo-reviews">Fotos pós-serviço</Link><Link href="/mowing-post-service-summaries">Resumos pós-serviço</Link></nav>
      {session ? <div className="session-context"><span>{session.user.display_name}</span><form action="/api/auth/logout" method="post"><input name="csrf_token" type="hidden" value={session.csrfToken} /><button type="submit">Sair</button></form></div> : <div className="update-context"><span>Dados</span><strong>preparados</strong></div>}
    </header>
    <section className="queue-heading">
      <div><p className="eyebrow">Revisão humana</p><h1>Fotos preparadas</h1><p className="subtitle">Qualidade visual e presença de régua, sem inferência automática de altura.</p></div>
      <div className="warning-banner" role="status"><span className="warning-icon" aria-hidden="true">!</span><div><strong>Nenhuma revisão autoriza campo</strong><span>Mesmo aceita, a foto não entra em treino ou relatório oficial.</span></div></div>
    </section>
    {operationMessage ? <p className="operation-message" role="status">{operationMessage}</p> : null}
    {!session || !queue ? <section className="reviewer-session"><div><strong>Sessão necessária</strong><span>Entre para acessar fotos da sua rodovia.</span></div><Link className="primary-button" href="/login">Entrar</Link></section> : <>
      <section className="reviewer-session"><div><strong>{session.user.display_name}</strong><span>{session.user.email}</span></div><div className="role-list">{session.road_roles.map((role) => <span key={`${role.road_code}-${role.role}`}>{role.road_code} · {role.role}</span>)}</div></section>
      <section className="queue-summary"><strong>{queue.result_count}</strong><span>foto(s) acessível(is)</span>{queue.truncated ? <small>Fila limitada a {queue.limit} itens.</small> : null}</section>
      {orderGroups.size > 0 ? <section className="prepared-summary-grid" aria-label="Resumos preparados por ordem">
        {[...orderGroups.entries()].map(([workOrderId, items]) => {
          const ordered = [...items].sort((left, right) => left.planned_point_sequence - right.planned_point_sequence);
          const first = ordered[0];
          if (!first) return null;
          const acceptedCount = ordered.filter(isAccepted).length;
          const sequences = new Set(ordered.map((item) => item.planned_point_sequence));
          const eligible = ordered.length === 3 && sequences.size === 3 &&
            [1, 2, 3].every((sequence) => sequences.has(sequence)) && acceptedCount === 3;
          const summary = summaryByOrder.get(workOrderId);
          const proposal = summary ? proposalBySummary.get(summary.summary_id) : undefined;
          const effectiveProposalRecommendation = proposal?.latest_review_decision === "adjusted"
            ? proposal.latest_adjusted_recommendation
            : proposal?.latest_review_decision === "accepted" ? proposal.recommendation : null;
          const rehearsal = proposal?.prepared_mowing_order_id
            ? rehearsalByMowingOrder.get(proposal.prepared_mowing_order_id) : undefined;
          const mowingSummary = proposal?.prepared_mowing_order_id
            ? mowingSummaryByOrder.get(proposal.prepared_mowing_order_id) : undefined;
          const mowingException = mowingSummary
            ? mowingExceptionBySummary.get(mowingSummary.summary_id) : undefined;
          return <article className="prepared-summary-card" key={workOrderId}>
            <div className="prepared-summary-heading"><div><p className="eyebrow">{first.road_code} · trecho #{first.segment_index} · {first.zone_type}</p><h2>Retorno dos três pontos</h2></div><span className={`status-pill ${summary ? "review" : "prepared"}`}>{summary ? "Resumo gerado" : `${acceptedCount}/3 aceitos`}</span></div>
            {summary ? <>
              <div className="summary-metrics"><div><strong>{formatHeight(summary.minimum_height_cm)} cm</strong><span>Mínima</span></div><div><strong>{formatHeight(summary.mean_height_cm)} cm</strong><span>Média</span></div><div><strong>{formatHeight(summary.maximum_height_cm)} cm</strong><span>Máxima</span></div></div>
              <div className="summary-classes"><span>N1 · {summary.n1_count}</span><span>N2 · {summary.n2_count}</span><span>N3 · {summary.n3_count}</span></div>
              <p className="summary-rationale">{summary.generation_rationale}</p>
              <small>Resultado preparado de medições digitadas em cenário simulado. Não é relatório oficial e não autoriza campo.</small>
              <form action={`/api/prepared-inspection-summaries/${summary.summary_id}/exports`} className="summary-export-form" method="post">
                <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
                <label htmlFor={`export-purpose-${summary.summary_id}`}>Propósito da exportação</label><input defaultValue="Compartilhar resultado preparado para revisão" id={`export-purpose-${summary.summary_id}`} maxLength={2000} name="export_purpose" required />
                <button className="secondary-button" type="submit">Baixar CSV preparado</button><small>O download gera um evento de auditoria imutável e mantém o bloqueio de relatório oficial.</small>
              </form>
              {proposal ? <>
                <div className="post-inspection-proposal">
                  <div><strong>{proposal.recommendation === "mowing_review" ? "Revisar proposta de roçada" : "Manter monitoramento"}</strong><span>Máxima {formatHeight(proposal.maximum_height_cm)} cm · limiar {formatHeight(proposal.applicable_threshold_cm)} cm</span>{proposal.latest_review_decision ? <span>Última decisão: {proposal.latest_review_decision}{proposal.latest_adjusted_recommendation ? ` → ${proposal.latest_adjusted_recommendation}` : ""}</span> : null}</div>
                  <span className="status-pill review">{proposal.review_state === "awaiting_review" ? "Decisão humana pendente" : "Decisão registrada"}</span>
                  <small>Regra {proposal.policy_version}. Mesmo aceita, a proposta não cria ordem, não autoriza roçada e não entra em relatório oficial.</small>
                </div>
                <form action={`/api/prepared-post-inspection-proposals/${proposal.proposal_id}/decisions`} className="decision-form proposal-review-form" method="post">
                  <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />{proposal.latest_review_id ? <input name="supersedes_review_id" type="hidden" value={proposal.latest_review_id} /> : null}
                  <div><label htmlFor={`proposal-decision-${proposal.proposal_id}`}>Decisão humana</label><select id={`proposal-decision-${proposal.proposal_id}`} name="decision"><option value="accepted">Aceitar para planejamento</option><option value="rejected">Rejeitar proposta</option><option value="adjusted">Ajustar ação</option></select></div>
                  <div><label htmlFor={`proposal-adjustment-${proposal.proposal_id}`}>Ajuste, se aplicável</label><select id={`proposal-adjustment-${proposal.proposal_id}`} name="adjusted_recommendation"><option value="">Selecione somente ao ajustar</option><option value="monitor">Monitorar</option><option value="mowing_review">Manter revisão de roçada</option></select></div>
                  <div className="decision-rationale"><label htmlFor={`proposal-review-rationale-${proposal.proposal_id}`}>Justificativa</label><textarea id={`proposal-review-rationale-${proposal.proposal_id}`} maxLength={2000} name="rationale" placeholder="Obrigatória ao rejeitar ou ajustar" rows={2} /></div>
                  <button className="primary-button" type="submit">{proposal.latest_review_id ? "Registrar correção auditável" : "Registrar decisão humana"}</button><small>Aceitar significa apenas concordar com o sinal preparado para planejamento; uso em campo permanece bloqueado.</small>
                </form>
                {proposal.prepared_mowing_order_id ? <>
                  <div className="post-inspection-proposal">
                    <div><strong>Ordem de roçada preparada</strong><span>ID {proposal.prepared_mowing_order_id}</span>{proposal.latest_resource_plan_id ? <span>Recursos candidatos: {proposal.latest_team_reference} · {proposal.latest_equipment_reference}</span> : null}</div><span className="status-pill prepared">Não executável</span>
                    <small>Equipe e equipamento continuam não atribuídos; as referências são placeholders pendentes de validação. Clima e segurança seguem pendentes.</small>
                  </div>
                  {rehearsal ? <div className="mowing-rehearsal-history">
                    <div className="rehearsal-history-heading"><div><strong>Histórico do ensaio de roçada</strong><span>Sequência append-only sincronizada pelo app</span></div><span className="status-pill simulated">{rehearsalStateLabel(rehearsal.rehearsal_state)}</span></div>
                    <dl className="rehearsal-metrics"><div><dt>Eventos</dt><dd>{rehearsal.event_count}</dd></div><div><dt>Pausas</dt><dd>{rehearsal.pause_count}</dd></div><div><dt>Intervalo registrado</dt><dd>{formatRecordedSpan(rehearsal.recorded_span_seconds)}</dd></div></dl>
                    {rehearsal.events.length > 0 ? <ol className="rehearsal-timeline">{rehearsal.events.map((event) => <li key={event.event_id}><i aria-hidden="true" /><div><strong>{rehearsalOperationLabel(event.operation)}</strong><time dateTime={event.client_occurred_at}>{formatRehearsalTime(event.client_occurred_at)}</time></div><span>{event.location_status === "simulated" ? "Local preparado" : "Sem localização"}</span></li>)}</ol> : <p className="rehearsal-empty">Nenhum evento de ensaio sincronizado.</p>}
                    <div className="mowing-post-service-history">
                      <div><strong>Alturas pós-serviço digitadas</strong><span className="status-pill simulated">{rehearsal.post_service_measurements.length}/3 sincronizadas</span></div>
                      {rehearsal.post_service_measurements.length > 0 ? <ol>{rehearsal.post_service_measurements.map((measurement) => <li key={measurement.event_id}><div><strong>Ponto preparado {measurement.source_point_sequence}</strong><time dateTime={measurement.client_captured_at}>{formatRehearsalTime(measurement.client_captured_at)}</time></div><span>{formatHeight(measurement.height_cm)} cm</span></li>)}</ol> : <p>Nenhuma altura pós-serviço sincronizada.</p>}
                      <div><strong>Fotos pós-serviço</strong><span className="status-pill simulated">{rehearsal.post_service_photo_reviews.filter((photo) => photo.review_state === "review_recorded").length}/{rehearsal.post_service_photo_reviews.length} revisadas</span></div>
                      {rehearsal.post_service_photo_reviews.length > 0 ? <ol>{rehearsal.post_service_photo_reviews.map((photo) => <li key={photo.photo_id}><div><strong>Ponto preparado {photo.source_point_sequence}</strong><span>{photo.latest_decision ? `Decisão ${photo.latest_decision}` : "Aguardando revisão"}</span></div><span>{photo.latest_ruler_status === "visible" ? "Régua visível" : photo.latest_ruler_status === null ? "Não revisada" : "Régua não confirmada"}</span></li>)}</ol> : <p>Nenhuma foto pós-serviço enviada.</p>}
                      <small>Entrada simulada e não verificada, sem GPS ou foto. Não é evidência de vegetação, eficácia ou conclusão da roçada.</small>
                    </div>
                    {mowingSummary ? <div className="mowing-post-service-history">
                      <div><strong>Resumo pós-serviço simulado</strong><span className="status-pill review">Gerado</span></div>
                      <div className="summary-metrics"><div><strong>{formatHeight(mowingSummary.minimum_height_cm)} cm</strong><span>Mínima</span></div><div><strong>{formatHeight(mowingSummary.mean_height_cm)} cm</strong><span>Média</span></div><div><strong>{formatHeight(mowingSummary.maximum_height_cm)} cm</strong><span>Máxima</span></div></div>
                      <div className="summary-classes"><span>N1 · {mowingSummary.n1_count}</span><span>N2 · {mowingSummary.n2_count}</span><span>N3 · {mowingSummary.n3_count}</span></div>
                      <p>{mowingSummary.generation_rationale}</p>
                      <small>Não comprova roçada, eficácia, conclusão, treinamento ou relatório oficial.</small>
                      <form action={`/api/prepared-mowing-post-service-summaries/${mowingSummary.summary_id}/exports`} className="summary-export-form" method="post">
                        <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
                        <label htmlFor={`mowing-export-purpose-${mowingSummary.summary_id}`}>Propósito da exportação</label><input defaultValue="Compartilhar pós-serviço simulado para revisão" id={`mowing-export-purpose-${mowingSummary.summary_id}`} maxLength={2000} name="export_purpose" required />
                        <button className="secondary-button" type="submit">Baixar CSV simulado</button><small>CSV auditado, simulado e inelegível para relatório oficial.</small>
                      </form>
                      {mowingException ? <div className="post-inspection-proposal">
                        <div><strong>{mowingPostServiceExceptionHeadline(mowingException)}</strong><span>Máxima {formatHeight(mowingException.maximum_height_cm)} cm · limiar {formatHeight(mowingException.applicable_threshold_cm)} cm</span>{mowingPostServiceExceptionEffectiveDecision(mowingException) ? <span>Decisão efetiva: {mowingPostServiceExceptionEffectiveDecision(mowingException)}</span> : null}</div><span className="status-pill review">{mowingPostServiceExceptionReviewStatus(mowingException)}</span>
                        <small>Regra {mowingException.policy_version}. Exceção simulada: não conclui roçada, não atualiza mapa e não autoriza campo.</small>
                        {mowingException.latest_review_rationale ? <p>{mowingException.latest_review_rationale}</p> : null}
                        <small>Revise ou corrija a decisão humana em <Link href="/mowing-post-service-summaries">Resumos pós-serviço</Link>.</small>
                      </div> : <form action={`/api/prepared-mowing-post-service-summaries/${mowingSummary.summary_id}/exceptions`} className="prepared-summary-form" method="post">
                        <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
                        <label htmlFor={`mowing-exception-rationale-${mowingSummary.summary_id}`}>Justificativa da avaliação de exceção</label><textarea defaultValue="Aplicar limiar preparado ao resumo pós-serviço simulado" id={`mowing-exception-rationale-${mowingSummary.summary_id}`} maxLength={2000} name="creation_rationale" required rows={2} />
                        <button className="primary-button" type="submit">Avaliar exceção pós-serviço</button><small>Se a máxima exceder o limiar, gera somente indicação de inspeção de seguimento com revisão humana.</small>
                      </form>}
                    </div> : rehearsal.post_service_measurements.length === 3 && rehearsal.post_service_photo_reviews.filter((photo) => photo.latest_decision === "accepted" && photo.latest_quality_status === "accepted" && photo.latest_ruler_status === "visible").length === 3 ? <form action={`/api/prepared-mowing-orders/${proposal.prepared_mowing_order_id}/post-service-summary`} className="prepared-summary-form" method="post">
                      <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
                      <label htmlFor={`mowing-summary-rationale-${proposal.prepared_mowing_order_id}`}>Justificativa da consolidação pós-serviço</label><textarea defaultValue="Consolidar o pós-serviço simulado após três medições e três revisões visuais aceitas" id={`mowing-summary-rationale-${proposal.prepared_mowing_order_id}`} maxLength={2000} name="generation_rationale" required rows={2} />
                      <button className="primary-button" type="submit">Gerar resumo pós-serviço</button><small>Calcula agregados apenas das alturas digitadas; fotos aceitas só fecham a completude visual. Não autoriza campo.</small>
                    </form> : <div className="summary-pending"><strong>Resumo pós-serviço pendente</strong><span>Exige três alturas digitadas e três fotos aceitas com qualidade aceita e régua visível.</span></div>}
                    <small>Estado simulado e não operacional. “Ensaio finalizado” não comprova execução ou conclusão oficial.</small>
                  </div> : null}
                  <form action={`/api/prepared-mowing-orders/${proposal.prepared_mowing_order_id}/resource-plans`} className="prepared-summary-form" method="post">
                    <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />{proposal.latest_resource_plan_id ? <input name="supersedes_plan_id" type="hidden" value={proposal.latest_resource_plan_id} /> : null}
                    <label htmlFor={`team-reference-${proposal.proposal_id}`}>Referência candidata de equipe</label><input defaultValue={proposal.latest_team_reference ?? "Equipe candidata — validar externamente"} id={`team-reference-${proposal.proposal_id}`} maxLength={200} name="team_reference" required />
                    <label htmlFor={`equipment-reference-${proposal.proposal_id}`}>Referência candidata de equipamento</label><input defaultValue={proposal.latest_equipment_reference ?? "Equipamento candidato — validar externamente"} id={`equipment-reference-${proposal.proposal_id}`} maxLength={200} name="equipment_reference" required />
                    <label htmlFor={`resource-rationale-${proposal.proposal_id}`}>Justificativa do plano de recursos</label><textarea defaultValue="Registrar candidatos preparados sem atribuir recursos operacionais" id={`resource-rationale-${proposal.proposal_id}`} maxLength={2000} name="planning_rationale" required rows={2} />
                    <button className="secondary-button" type="submit">{proposal.latest_resource_plan_id ? "Corrigir plano de recursos" : "Registrar recursos candidatos"}</button><small>O registro é append-only, não confirma disponibilidade e não atribui equipe ou equipamento.</small>
                  </form>
                  {proposal.latest_resource_plan_id ? <>
                    {proposal.latest_readiness_assessment_id ? <div className="post-inspection-proposal"><div><strong>Avaliação manual preparada</strong><span>Clima: {proposal.latest_weather_result} · Segurança: {proposal.latest_safety_result}</span></div><span className="status-pill review">Validação pendente</span><small>Fontes declaradas: {proposal.latest_weather_source_reference} · {proposal.latest_safety_source_reference}. Mesmo “clear” não libera execução.</small></div> : null}
                    <form action={`/api/prepared-mowing-orders/${proposal.prepared_mowing_order_id}/readiness-assessments`} className="prepared-summary-form" method="post">
                      <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} /><input name="resource_plan_id" type="hidden" value={proposal.latest_resource_plan_id} />{proposal.latest_readiness_assessment_id ? <input name="supersedes_assessment_id" type="hidden" value={proposal.latest_readiness_assessment_id} /> : null}
                      <label htmlFor={`weather-result-${proposal.proposal_id}`}>Resultado manual de clima</label><select id={`weather-result-${proposal.proposal_id}`} name="weather_result"><option value="inconclusive">Inconclusivo</option><option value="clear">Sem bloqueio identificado</option><option value="blocked">Bloqueado</option></select>
                      <label htmlFor={`weather-source-${proposal.proposal_id}`}>Fonte declarada de clima</label><input id={`weather-source-${proposal.proposal_id}`} maxLength={500} name="weather_source_reference" placeholder="Consulta manual e horário — validar externamente" required />
                      <label htmlFor={`safety-result-${proposal.proposal_id}`}>Resultado manual de segurança</label><select id={`safety-result-${proposal.proposal_id}`} name="safety_result"><option value="inconclusive">Inconclusivo</option><option value="clear">Sem bloqueio identificado</option><option value="blocked">Bloqueado</option></select>
                      <label htmlFor={`safety-source-${proposal.proposal_id}`}>Fonte declarada de segurança</label><input id={`safety-source-${proposal.proposal_id}`} maxLength={500} name="safety_source_reference" placeholder="Checklist ou referência — validar externamente" required />
                      <label htmlFor={`readiness-rationale-${proposal.proposal_id}`}>Justificativa da avaliação</label><textarea defaultValue="Registrar avaliação manual preparada sem liberar execução" id={`readiness-rationale-${proposal.proposal_id}`} maxLength={2000} name="assessment_rationale" required rows={2} />
                      <button className="secondary-button" type="submit">{proposal.latest_readiness_assessment_id ? "Corrigir avaliação" : "Registrar avaliação manual"}</button><small>Resultados são declarações preparadas pendentes de validação e nunca substituem aprovação operacional.</small>
                    </form>
                    {proposal.latest_readiness_assessment_id ? <>
                      {proposal.latest_planning_approval_id ? <div className="post-inspection-proposal"><div><strong>Decisão de planejamento: {proposal.latest_planning_decision}</strong><span>{proposal.latest_planning_decision_rationale}</span></div><span className="status-pill review">Somente planejamento</span><small>Aprovação operacional não satisfeita; regra de aprovação dupla ainda depende de política oficial.</small></div> : null}
                      <form action={`/api/prepared-mowing-orders/${proposal.prepared_mowing_order_id}/planning-approvals`} className="prepared-summary-form" method="post">
                        <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} /><input name="readiness_assessment_id" type="hidden" value={proposal.latest_readiness_assessment_id} />{proposal.latest_planning_approval_id ? <input name="supersedes_approval_id" type="hidden" value={proposal.latest_planning_approval_id} /> : null}
                        <label htmlFor={`planning-decision-${proposal.proposal_id}`}>Decisão segregada</label><select defaultValue={proposal.latest_weather_result === "clear" && proposal.latest_safety_result === "clear" ? "approved_for_planning" : "changes_requested"} id={`planning-decision-${proposal.proposal_id}`} name="decision"><option disabled={proposal.latest_weather_result !== "clear" || proposal.latest_safety_result !== "clear"} value="approved_for_planning">Aprovar somente para planejamento</option><option value="changes_requested">Solicitar alterações</option><option value="rejected">Rejeitar planejamento</option></select>
                        <label htmlFor={`planning-decision-rationale-${proposal.proposal_id}`}>Justificativa da decisão</label><textarea defaultValue="Registrar decisão sobre o cenário preparado sem autorizar execução" id={`planning-decision-rationale-${proposal.proposal_id}`} maxLength={2000} name="decision_rationale" required rows={2} />
                        <button className="secondary-button" type="submit">{proposal.latest_planning_approval_id ? "Corrigir decisão de planejamento" : "Registrar decisão de planejamento"}</button><small>Mesmo aprovada, a ordem permanece simulada, não executável e sujeita à política oficial de aprovação.</small>
                      </form>
                    </> : null}
                  </> : null}
                </> : effectiveProposalRecommendation === "mowing_review" && proposal.latest_review_id ? <form action="/api/prepared-mowing-orders" className="prepared-summary-form" method="post">
                  <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} /><input name="source_review_id" type="hidden" value={proposal.latest_review_id} />
                  <label htmlFor={`mowing-rationale-${proposal.proposal_id}`}>Justificativa do planejamento de roçada</label><textarea defaultValue="Preparar ordem de roçada sem liberar execução operacional" id={`mowing-rationale-${proposal.proposal_id}`} maxLength={2000} name="planning_rationale" required rows={2} />
                  <button className="primary-button" type="submit">Preparar ordem de roçada</button><small>Cria apenas a fundação de planejamento. Não atribui equipe/equipamento, não verifica clima/segurança e não autoriza campo.</small>
                </form> : null}
              </> : <form action={`/api/prepared-inspection-summaries/${summary.summary_id}/post-inspection-proposal`} className="prepared-summary-form" method="post">
                <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
                <label htmlFor={`proposal-rationale-${summary.summary_id}`}>Justificativa para aplicar a regra pós-inspeção</label><textarea defaultValue="Aplicar a regra preparada de limiar ao retorno revisado" id={`proposal-rationale-${summary.summary_id}`} maxLength={2000} name="creation_rationale" required rows={2} />
                <button className="primary-button" type="submit">Gerar proposta preparada</button><small>Compara a máxima digitada com 10 cm em área especial ou 30 cm nas demais zonas. Exige revisão humana posterior.</small>
              </form>}
            </> : eligible ? <form action={`/api/work-orders/${workOrderId}/prepared-summary`} className="prepared-summary-form" method="post">
              <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />
              <label htmlFor={`summary-rationale-${workOrderId}`}>Justificativa da consolidação</label><textarea defaultValue="Consolidar o retorno preparado dos três pontos revisados" id={`summary-rationale-${workOrderId}`} maxLength={2000} name="generation_rationale" required rows={2} />
              <button className="primary-button" type="submit">Gerar resumo preparado</button><small>Calcula N1/N2/N3 e médias apenas das medições digitadas; as fotos confirmam somente a completude revisada.</small>
            </form> : <div className="summary-pending"><strong>Evidência ainda incompleta</strong><span>Revise os três pontos com qualidade aceita e régua visível. A foto não mede altura.</span></div>}
          </article>;
        })}
      </section> : null}
      <section className="photo-review-grid" aria-label="Fotos para revisão">
        {queue.items.length === 0 ? <div className="queue-empty"><h2>Fila vazia</h2><p>Nenhuma foto preparada está disponível para seu papel.</p></div> : queue.items.map((item) => <article className="photo-review-card" key={item.photo_id}>
          <div className="photo-frame"><Image alt={`Foto preparada do ponto ${item.planned_point_sequence}`} fill sizes="(max-width: 720px) 92vw, 42vw" src={`/api/media/${item.photo_id}`} unoptimized /></div>
          <div className="photo-review-body">
            <div className="recommendation-title"><div><p className="eyebrow">{item.road_code} · trecho #{item.segment_index} · {item.zone_type}</p><h2>Ponto {item.planned_point_sequence}</h2></div><span className="status-pill review">{item.review_state === "awaiting_review" ? "Aguardando revisão" : "Revisão registrada"}</span></div>
            <p className="photo-meta">{item.media_type} · {item.byte_size} bytes · conteúdo preparado e não oficial</p>
            {item.latest_review_id ? <div className="latest-photo-review"><strong>Última revisão: {item.latest_decision}</strong><span>Qualidade {item.latest_quality_status} · régua {item.latest_ruler_status}</span>{item.latest_rationale ? <p>{item.latest_rationale}</p> : null}</div> : null}
            <form action={`/api/media/${item.photo_id}/reviews`} className="decision-form" method="post">
              <input name="csrf_token" type="hidden" value={session.csrfToken} /><input name="idempotency_key" type="hidden" value={randomUUID()} />{item.latest_review_id ? <input name="supersedes_review_id" type="hidden" value={item.latest_review_id} /> : null}
              <div><label htmlFor={`decision-${item.photo_id}`}>Decisão</label><select id={`decision-${item.photo_id}`} name="decision"><option value="accepted">Aceitar</option><option value="rejected">Rejeitar</option><option value="inconclusive">Inconclusiva</option></select></div>
              <div><label htmlFor={`quality-${item.photo_id}`}>Qualidade</label><select id={`quality-${item.photo_id}`} name="quality_status"><option value="accepted">Aceita</option><option value="rejected">Rejeitada</option><option value="inconclusive">Inconclusiva</option></select></div>
              <div><label htmlFor={`ruler-${item.photo_id}`}>Régua</label><select id={`ruler-${item.photo_id}`} name="ruler_status"><option value="visible">Visível</option><option value="not_visible">Não visível</option><option value="inconclusive">Inconclusiva</option></select></div>
              <div className="decision-rationale"><label htmlFor={`rationale-${item.photo_id}`}>Justificativa</label><textarea id={`rationale-${item.photo_id}`} maxLength={2000} name="rationale" placeholder="Obrigatória para rejeição ou inconclusão" rows={3} /></div>
              <button className="primary-button" type="submit">{item.latest_review_id ? "Registrar correção" : "Registrar revisão"}</button><small>“Régua visível” não valida altura e não promove evidência.</small>
            </form>
          </div>
        </article>)}
      </section>
    </>}
  </main>;
}
