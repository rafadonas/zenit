import Link from "next/link";

export type DashboardArea = "overview" | "corridor" | "decisions" | "field" | "results";

interface HeaderSession {
  csrfToken: string;
  displayName: string;
}

interface DashboardHeaderProps {
  active: DashboardArea;
  context?: {
    label: string;
    value: string;
  };
  session?: HeaderSession | null;
}

const navigation: Array<{ area: DashboardArea; href: string; label: string }> = [
  { area: "overview", href: "/overview", label: "Visão geral" },
  { area: "corridor", href: "/corridor", label: "Mapa" },
  { area: "decisions", href: "/recommendations", label: "Decisões" },
  { area: "field", href: "/photo-reviews", label: "Campo" },
  { area: "results", href: "/mowing-post-service-summaries", label: "Resultados" },
];

export function DashboardHeader({ active, context, session }: DashboardHeaderProps) {
  return (
    <header className="topbar">
      <Link className="brand-block" href="/overview" aria-label="ZENIT — visão geral">
        <span className="brand-mark" aria-hidden="true"><i /></span>
        <span><strong>ZENIT</strong><small>Vegetação rodoviária</small></span>
      </Link>
      <nav className="topnav" aria-label="Navegação principal">
        {navigation.map((item) => (
          <Link
            aria-current={active === item.area ? "page" : undefined}
            href={item.href}
            key={item.area}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {session ? (
        <div className="session-context">
          <span>{session.displayName}</span>
          <form action="/api/auth/logout" method="post">
            <input name="csrf_token" type="hidden" value={session.csrfToken} />
            <button type="submit">Sair</button>
          </form>
        </div>
      ) : context ? (
        <div className="update-context"><span>{context.label}</span><strong>{context.value}</strong></div>
      ) : null}
    </header>
  );
}
