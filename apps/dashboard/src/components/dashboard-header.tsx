import Link from "next/link";

export type DashboardArea = "overview" | "corridor" | "decisions" | "field" | "results";

interface HeaderSession {
  csrfToken: string;
  displayName: string;
  roadRoles?: Array<{
    dataStatus: "real" | "prepared" | "simulated";
    roadCode: string;
    role: "manager" | "supervisor";
  }>;
}

interface DashboardHeaderProps {
  active: DashboardArea;
  context?: {
    label: string;
    value: string;
  };
  session?: HeaderSession | null;
}

const navigation: Array<{ area: DashboardArea; href: string; label: string; shortLabel: string }> = [
  { area: "overview", href: "/overview", label: "Visão geral", shortLabel: "Visão" },
  { area: "corridor", href: "/corridor", label: "Mapa", shortLabel: "Mapa" },
  { area: "decisions", href: "/recommendations", label: "Decisões", shortLabel: "Decidir" },
  { area: "field", href: "/photo-reviews", label: "Campo", shortLabel: "Campo" },
  { area: "results", href: "/mowing-post-service-summaries", label: "Resultados", shortLabel: "Result." },
];

export function DashboardHeader({ active, context, session }: DashboardHeaderProps) {
  const activeItem = navigation.find((item) => item.area === active);
  const primaryRole = session?.roadRoles?.[0];
  const roleContext = primaryRole
    ? `${primaryRole.role === "manager" ? "Gestor" : "Supervisor"} · ${primaryRole.roadCode}`
    : null;

  return (
    <header className="topbar">
      <Link className="brand-block" href="/overview" aria-label="ZENIT — visão geral">
        <span className="brand-mark" aria-hidden="true"><i /></span>
        <span><strong>ZENIT</strong><small>Vegetação rodoviária</small></span>
      </Link>
      <div className="route-context" aria-label="Contexto da página">
        <span>{context?.label ?? "Área"}</span>
        <strong>{context?.value ?? activeItem?.label}</strong>
      </div>
      <nav className="topnav" aria-label="Navegação principal">
        {navigation.map((item) => (
          <Link
            aria-current={active === item.area ? "page" : undefined}
            data-compact-label={item.shortLabel}
            href={item.href}
            key={item.area}
            title={item.label}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {session ? (
        <div className="session-context">
          <span className="session-context__name">{session.displayName}</span>
          {roleContext ? (
            <span className="session-context__role" data-status={primaryRole?.dataStatus}>
              {roleContext}
            </span>
          ) : null}
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
