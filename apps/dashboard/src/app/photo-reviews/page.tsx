import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";
import Image from "next/image";
import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import { isPhotoReviewQueue, type PhotoReviewQueue } from "../../lib/photo-reviews";
import {
  isPreparedSummaryCollection, type PreparedInspectionSummary,
  type PreparedSummaryCollection,
} from "../../lib/prepared-summaries";
import { SESSION_COOKIE_NAME } from "../../lib/session-security";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{ review?: string; summary?: string; export?: string }>;
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

function message(review?: string, summary?: string, exportStatus?: string): string | null {
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

export default async function PhotoReviewsPage({ searchParams }: PageProps) {
  const [session, queue, summaries, query] = await Promise.all([
    loadDashboardSession(), loadQueue(), loadSummaries(), searchParams,
  ]);
  const operationMessage = message(query.review, query.summary, query.export);
  const summaryByOrder = new Map<string, PreparedInspectionSummary>(
    summaries?.items.map((summary) => [summary.work_order_id, summary]) ?? [],
  );
  const orderGroups = new Map<string, PhotoReviewQueue["items"]>();
  for (const item of queue?.items ?? []) {
    const group = orderGroups.get(item.work_order_id) ?? [];
    group.push(item);
    orderGroups.set(item.work_order_id, group);
  }
  return <main className="recommendations-shell">
    <header className="topbar">
      <div className="brand-block"><span className="brand-mark" aria-hidden="true"><i /></span><div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div></div>
      <nav className="topnav" aria-label="Navegação principal"><Link href="/">Corredor</Link><Link href="/recommendations">Recomendações</Link><Link aria-current="page" href="/photo-reviews">Fotos</Link></nav>
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
