import { LogOut, Scale, UserRound } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { APP_NAME } from "@/config/app";
import { useAuth } from "@/features/auth/authState";
import { paths } from "@/routes/paths";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive
      ? "bg-accent-soft text-accent"
      : "text-fg-muted hover:bg-surface-muted hover:text-fg"
  }`;

export const AppLayout = () => {
  const { user, signOut } = useAuth();

  return (
    <div className="flex h-dvh flex-col print:block print:h-auto">
      <header className="flex h-14 shrink-0 items-center gap-6 border-b border-border bg-surface px-4 print:hidden">
        <Link
          to={paths.projects()}
          className="flex items-center gap-2 font-semibold"
        >
          <Scale className="size-5 text-accent" aria-hidden />
          <span>{APP_NAME}</span>
        </Link>
        <nav aria-label="Navegação principal" className="flex gap-1">
          <NavLink to={paths.projects()} className={navLinkClass}>
            Projetos
          </NavLink>
        </nav>
        <span className="ml-auto hidden text-xs text-fg-muted lg:block">
          Análise preliminar · apoio à decisão
        </span>
        {user && (
          <div className="ml-auto flex items-center gap-2 lg:ml-0">
            <span className="hidden items-center gap-1.5 text-sm sm:flex">
              <UserRound className="size-4 text-fg-muted" aria-hidden />
              {user.name}
            </span>
            <button type="button" className="btn-ghost" onClick={signOut} title="Sair">
              <LogOut className="size-4" aria-hidden />
              <span className="sr-only sm:not-sr-only">Sair</span>
            </button>
          </div>
        )}
      </header>
      {/* relative: absolutely positioned descendants (e.g. sr-only) must not overflow the document */}
      <main className="relative flex min-h-0 flex-1 flex-col overflow-auto print:block print:overflow-visible">
        <Outlet />
      </main>
    </div>
  );
};
