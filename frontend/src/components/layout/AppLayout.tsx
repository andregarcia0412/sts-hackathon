import { LogOut } from "lucide-react";
import { Link, Outlet, useLocation, useMatch } from "react-router-dom";
import logoBnb from "@/assets/logo-bnb.svg";
import { KeyboardArrowRightIcon } from "@/components/icons/MaterialIcons";
import { APP_NAME } from "@/config/app";
import { useAuth } from "@/features/auth/authState";
import { NEW_PROJECT_PARAM, paths } from "@/routes/paths";

type StepKey = "projects" | "upload" | "analysis" | "decision";

interface Step {
  key: StepKey;
  label: string;
  /** Unavailable outside a project (no analysis or decision to open) */
  to: string | null;
}

/** Flow of the analyst: Projetos › Upload › Grafo de evidências › Documento de decisão */
const useSteps = (): { steps: Step[]; current: StepKey | null } => {
  const analysis = useMatch("/projetos/:projectId/analise");
  const decision = useMatch("/projetos/:projectId/decisao");
  const projects = useMatch("/projetos");
  const { search } = useLocation();
  const projectId = (analysis ?? decision)?.params.projectId;

  // On the list, opening the upload keeps the filters in the URL
  const uploadSearch = new URLSearchParams(projects ? search : "");
  uploadSearch.set(NEW_PROJECT_PARAM, "1");

  return {
    steps: [
      { key: "projects", label: "Projetos", to: paths.projects() },
      { key: "upload", label: "Upload de arquivos", to: `${paths.projects()}?${uploadSearch}` },
      {
        key: "analysis",
        label: "Grafo de evidências",
        to: projectId ? paths.analysis(projectId) : null,
      },
      {
        key: "decision",
        label: "Documento de decisão",
        to: projectId ? paths.decision(projectId) : null,
      },
    ],
    current: analysis ? "analysis" : decision ? "decision" : projects ? "projects" : null,
  };
};

const stepClass = "flex items-center px-2.5 py-1.5 text-base leading-5 whitespace-nowrap";

const Stepper = () => {
  const { steps, current } = useSteps();

  return (
    <nav aria-label="Etapas da análise" className="max-w-full overflow-x-auto">
      <ol className="flex items-center gap-2">
        {steps.map((step, i) => (
          <li key={step.key} className="flex items-center gap-2">
            {i > 0 && <KeyboardArrowRightIcon className="size-6 shrink-0 text-fg-faint" />}
            {step.key === current ? (
              <span
                aria-current="step"
                className={`${stepClass} border-b border-action bg-accent-soft font-bold text-accent`}
              >
                {step.label}
              </span>
            ) : step.to ? (
              <Link
                to={step.to}
                className={`${stepClass} rounded-2xl font-medium text-fg-faint transition-colors hover:text-fg-secondary`}
              >
                {step.label}
              </Link>
            ) : (
              <span aria-disabled className={`${stepClass} font-medium text-fg-faint/60`}>
                {step.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};

const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

export const AppLayout = () => {
  const { user, signOut } = useAuth();

  return (
    <div className="relative isolate flex h-dvh flex-col overflow-hidden bg-canvas print:block print:h-auto print:overflow-visible print:bg-white">
      {/* Background glows of the design (wine top-left, orange bottom-right) */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden print:hidden">
        <div className="absolute -top-60 -left-96 size-[594px] rounded-full bg-action opacity-60 blur-[180px]" />
        <div className="absolute -right-96 -bottom-80 size-[594px] rounded-full bg-brand-orange opacity-60 blur-[180px]" />
      </div>

      <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-border bg-white/50 px-4 pt-6 pb-4 sm:px-10 print:hidden">
        <Link to={paths.projects()} className="shrink-0 rounded-sm p-[3px]">
          <img src={logoBnb} alt={`Banco do Nordeste · ${APP_NAME}`} width={101} height={36} />
        </Link>
        <div className="order-last w-full lg:order-none lg:w-auto">
          <Stepper />
        </div>
        {user && (
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="flex size-10 items-center justify-center rounded-full bg-surface-sunken text-sm font-semibold text-fg-secondary"
            >
              {initials(user.name)}
            </span>
            <span className="text-sm leading-5 text-fg-soft">{user.name}</span>
            <button
              type="button"
              className="btn-ghost ml-1 p-2"
              onClick={signOut}
              title="Sair"
            >
              <LogOut className="size-4" aria-hidden />
              <span className="sr-only">Sair</span>
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
