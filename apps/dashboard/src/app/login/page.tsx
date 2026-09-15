import Link from "next/link";
import { redirect } from "next/navigation";

import { LoginForm } from "../../components/login-form";
import { loadDashboardSession } from "../../lib/dashboard-session";
import {
  getFixedDashboardSessionConfig,
  safeDashboardReturnPath,
} from "../../lib/fixed-dashboard-session";
import { getLoginNotice } from "../../lib/login-messages";

export const dynamic = "force-dynamic";

interface LoginPageProps {
  searchParams: Promise<{ error?: string; return_to?: string; status?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const fixedSession = getFixedDashboardSessionConfig();
  const session = await loadDashboardSession();
  if (session) redirect(fixedSession?.homePath ?? "/recommendations");
  const query = await searchParams;
  const notice = getLoginNotice(query.error, query.status);
  const requestedReturnTo = query.return_to
    ? safeDashboardReturnPath(query.return_to, "")
    : "";
  const returnTo = requestedReturnTo || "/recommendations?auth=signed-in";

  return (
    <main
      className="login-shell"
      data-zenit-smoke-page="login"
      id="main-content"
      tabIndex={-1}
    >
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand-panel">
          <div className="login-brand">
            <span className="brand-mark" aria-hidden="true"><i /></span>
            <div><strong>ZENIT</strong><small>Vegetation intelligence</small></div>
          </div>
          <div className="login-brand-copy">
            <p className="eyebrow">Dados que orientam</p>
            <h2>Melhores caminhos.</h2>
            <p>Monitoramento inteligente da vegetação para uma operação mais segura e eficiente.</p>
          </div>
          <div className="login-brand-orbit orbit-one" aria-hidden="true" />
          <div className="login-brand-orbit orbit-two" aria-hidden="true" />
        </div>
        <div className="login-form-panel">
          <div className="login-context" aria-label="Contexto de acesso">
            <div><span>Ambiente</span><strong>{fixedSession ? "Demonstração local" : "MVP local"}</strong></div>
            <div><span>Perfil</span><strong>{fixedSession ? "Configurado para esta porta" : "Confirmado após a entrada"}</strong></div>
          </div>
          <h1 id="login-title">Entrar na plataforma</h1>
          <p className="subtitle">
            {fixedSession
              ? "Esta porta usa um perfil demonstrativo fixo. Não é necessário informar e-mail ou senha."
              : "A identidade autenticada será vinculada à decisão. Nenhuma revisão autoriza trabalho de campo."}
          </p>
          {notice ? (
            <div
              className={`form-message ${notice.tone}`}
              role={notice.tone === "error" ? "alert" : "status"}
            >
              <strong>{notice.title}</strong>
              <span>{notice.detail}</span>
            </div>
          ) : null}
          {fixedSession ? (
            <div className="demo-access-card">
              <span>Perfil configurado nesta porta</span>
              <strong>{fixedSession.email}</strong>
              <small>
                O gestor usa a porta 3000 e o supervisor usa a porta 3002 no Compose local.
              </small>
              <Link
                className="primary-button"
                href={`/api/auth/fixed-session?return_to=${encodeURIComponent(requestedReturnTo || fixedSession.homePath)}`}
              >
                Acessar demonstração
              </Link>
            </div>
          ) : <LoginForm returnTo={returnTo} />}
          <div className="login-safety-note">
            <strong>Identidade local do MVP</strong>
            <span>A sessão fica em cookie protegido no servidor. Não use credenciais corporativas ou senhas reutilizadas.</span>
          </div>
          <Link href="/overview">Continuar pela visão geral somente leitura</Link>
        </div>
      </section>
    </main>
  );
}
