import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";
import Image from "next/image";
import Link from "next/link";

import { loadDashboardSession } from "../../lib/dashboard-session";
import { isPhotoReviewQueue, type PhotoReviewQueue } from "../../lib/photo-reviews";
import { SESSION_COOKIE_NAME } from "../../lib/session-security";

export const dynamic = "force-dynamic";

interface PageProps { searchParams: Promise<{ review?: string }>; }

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

function message(status?: string): string | null {
  if (status === "recorded") return "Revisão humana registrada na trilha append-only.";
  if (status === "forbidden") return "Seu usuário não pode revisar esta foto.";
  if (status === "missing") return "A foto preparada não foi encontrada.";
  if (status === "conflict") return "A chave de repetição ou revisão anterior entrou em conflito.";
  if (status === "invalid") return "A revisão está incompleta ou inconsistente.";
  if (status === "service-unavailable") return "O serviço de revisão não está disponível agora.";
  return null;
}

export default async function PhotoReviewsPage({ searchParams }: PageProps) {
  const [session, queue, query] = await Promise.all([
    loadDashboardSession(), loadQueue(), searchParams,
  ]);
  const operationMessage = message(query.review);
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
