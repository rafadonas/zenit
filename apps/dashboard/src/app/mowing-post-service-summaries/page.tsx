import { cookies } from "next/headers";
import Link from "next/link";
import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  isMowingPostServiceSummaryCollection,
  type MowingPostServiceSummaryCollection,
} from "../../lib/mowing-post-service-summaries";
import { SESSION_COOKIE_NAME } from "../../lib/session-security";

export const dynamic = "force-dynamic";

async function loadSummaries(): Promise<MowingPostServiceSummaryCollection | null> {
  const token = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const response = await fetch(
    `${process.env.INTERNAL_API_URL ?? "http://localhost:8000"}/v1/prepared-mowing-post-service-summaries?limit=50`,
    { cache: "no-store", headers: { Authorization: `Bearer ${token}` } },
  );
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`Mowing post-service summaries returned HTTP ${response.status}`);
  const payload: unknown = await response.json();
  if (!isMowingPostServiceSummaryCollection(payload)) {
    throw new Error("Mowing post-service summary safety contract is invalid");
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

export default async function MowingPostServiceSummariesPage() {
  const [session, summaries] = await Promise.all([loadDashboardSession(), loadSummaries()]);
  return <main className="recommendations-shell">
    <header className="topbar"><div className="brand-block"><span className="brand-mark" aria-hidden="true"><i /></span><div><strong>ZENIT</strong><small>Vegetação rodoviária</small></div></div><nav className="topnav" aria-label="Navegação principal"><Link href="/">Corredor</Link><Link href="/recommendations">Recomendações</Link><Link href="/photo-reviews">Fotos de inspeção</Link><Link href="/mowing-photo-reviews">Fotos pós-serviço</Link><Link aria-current="page" href="/mowing-post-service-summaries">Resumos pós-serviço</Link></nav>{session ? <div className="session-context"><span>{session.user.display_name}</span><form action="/api/auth/logout" method="post"><input name="csrf_token" type="hidden" value={session.csrfToken} /><button type="submit">Sair</button></form></div> : null}</header>
    <section className="queue-heading"><div><p className="eyebrow">Agregação · pós-serviço simulado</p><h1>Resumos do ensaio de roçada</h1><p className="subtitle">Consulta somente leitura dos agregados gerados após três medições digitadas e três revisões visuais aceitas.</p></div><div className="warning-banner" role="status"><span className="warning-icon" aria-hidden="true">!</span><div><strong>Não é conclusão operacional</strong><span>O resumo não comprova roçada, eficácia, campo, treinamento ou relatório oficial.</span></div></div></section>
    {!session || !summaries ? <section className="reviewer-session"><div><strong>Sessão necessária</strong><span>Entre para acessar resumos pós-serviço da sua rodovia.</span></div><Link className="primary-button" href="/login">Entrar</Link></section> : <><section className="reviewer-session"><div><strong>{session.user.display_name}</strong><span>{session.user.email}</span></div><div className="role-list">{session.road_roles.map((role) => <span key={`${role.road_code}-${role.role}`}>{role.road_code} · {role.role}</span>)}</div></section><section className="queue-summary"><strong>{summaries.result_count}</strong><span>resumo(s) pós-serviço acessível(is)</span>{summaries.truncated ? <small>Lista limitada a {summaries.limit} itens.</small> : null}</section><p className="quality-note"><span>i</span><span><strong>Escopo seguro</strong> {summaries.warning}</span></p><section className="prepared-summary-grid" aria-label="Resumos pós-serviço simulados">{summaries.items.length === 0 ? <div className="queue-empty"><h2>Nenhum resumo</h2><p>Não há resumo pós-serviço simulado disponível para seu papel.</p></div> : summaries.items.map((item) => <article className="prepared-summary-card" key={item.summary_id}><div className="prepared-summary-heading"><div><p className="eyebrow">Ordem {item.mowing_order_id}</p><h2>Resumo pós-serviço</h2></div><span className="status-pill simulated">Simulado</span></div><dl className="summary-metrics"><div><dt>Mínima</dt><dd>{cm(item.minimum_height_cm)}</dd></div><div><dt>Média</dt><dd>{cm(item.mean_height_cm)}</dd></div><div><dt>Máxima</dt><dd>{cm(item.maximum_height_cm)}</dd></div></dl><div className="summary-classes"><span>N1 {item.n1_count}</span><span>N2 {item.n2_count}</span><span>N3 {item.n3_count}</span></div><p className="summary-rationale">{item.generation_rationale}</p><small>{item.summary_policy_version} · gerado {formatDate(item.generated_at)} · {item.measurement_count} medições · {item.accepted_photo_review_count} fotos aceitas</small></article>)}</section></>}
  </main>;
}
