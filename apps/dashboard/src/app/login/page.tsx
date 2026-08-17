import Link from "next/link";
import { redirect } from "next/navigation";

import { loadDashboardSession } from "../../lib/dashboard-session";

export const dynamic = "force-dynamic";

interface LoginPageProps {
  searchParams: Promise<{ error?: string; status?: string }>;
}

function loginMessage(error: string | undefined, status: string | undefined): string | null {
  if (status === "signed-out") return "Sessão encerrada com segurança.";
  if (status === "signed-out-local") {
    return "Sessão local encerrada; a revogação remota não pôde ser confirmada.";
  }
  if (error === "credentials") return "E-mail ou senha inválidos.";
  if (error === "rate-limited") return "Muitas tentativas. Aguarde antes de tentar novamente.";
  if (error === "session") return "Sua sessão expirou. Entre novamente.";
  if (error === "service-unavailable") return "Autenticação indisponível no momento.";
  if (error === "invalid-request") return "Revise os campos e tente novamente.";
  return null;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const session = await loadDashboardSession();
  if (session) redirect("/recommendations");
  const query = await searchParams;
  const message = loginMessage(query.error, query.status);

  return (
    <main
      className="login-shell"
      data-zenit-smoke-page="login"
      id="main-content"
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
          <p className="eyebrow">Acesso local do MVP</p>
          <h1 id="login-title">Entrar na plataforma</h1>
          <p className="subtitle">
            A identidade autenticada será vinculada à decisão. Nenhuma revisão autoriza trabalho de campo.
          </p>
          {message ? <p className="form-message" role="status">{message}</p> : null}
          <form action="/api/auth/session" className="login-form" method="post">
            <label htmlFor="email">E-mail</label>
            <input
              autoComplete="username"
              id="email"
              maxLength={320}
              name="email"
              placeholder="nome@empresa.com"
              required
              type="email"
            />
            <label htmlFor="password">Senha</label>
            <input
              autoComplete="current-password"
              id="password"
              maxLength={1024}
              name="password"
              required
              type="password"
            />
            <button className="primary-button" type="submit">Entrar</button>
          </form>
          <div className="login-safety-note">
            <strong>Identidade local do MVP</strong>
            <span>Não use credenciais corporativas ou senhas reutilizadas.</span>
          </div>
          <Link href="/recommendations">Voltar para a fila somente leitura</Link>
        </div>
      </section>
    </main>
  );
}
