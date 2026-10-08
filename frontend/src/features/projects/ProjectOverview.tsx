import { CircleAlert, CircleCheckBig, FileSearch, FolderOpen, LoaderCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ProjectStatus } from "@/domain/types";

const TILES: { status: ProjectStatus | null; label: string; Icon: LucideIcon; icon: string }[] = [
  { status: null, label: "Todos os meus projetos", Icon: FolderOpen, icon: "text-fg-muted" },
  { status: "ready", label: "Prontos para análise", Icon: FileSearch, icon: "text-accent" },
  { status: "decided", label: "Decididos", Icon: CircleCheckBig, icon: "text-score-strong" },
  { status: "processing", label: "Processando", Icon: LoaderCircle, icon: "text-fg-muted" },
  { status: "error", label: "Com erro", Icon: CircleAlert, icon: "text-danger" },
];

interface ProjectOverviewProps {
  counts: Record<ProjectStatus, number>;
  /** Status filter currently applied (single status from the tiles) */
  selected: ProjectStatus[];
  onSelect: (statuses: ProjectStatus[]) => void;
}

/** Counts per status; each tile is also a quick filter */
export const ProjectOverview = ({ counts, selected, onSelect }: ProjectOverviewProps) => {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <ul aria-label="Resumo dos meus projetos" className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {TILES.map(({ status, label, Icon, icon }) => {
        const value = status ? counts[status] : total;
        const active = status
          ? selected.length === 1 && selected[0] === status
          : selected.length === 0;
        return (
          <li key={label}>
            <button
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(status && !active ? [status] : [])}
              className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                active
                  ? "border-accent bg-accent-soft"
                  : "border-border bg-surface hover:border-border-strong"
              }`}
            >
              <Icon className={`size-5 shrink-0 ${icon}`} aria-hidden />
              <span className="min-w-0">
                <span className="block text-xl leading-tight font-semibold tabular-nums">{value}</span>
                <span className="block truncate text-xs text-fg-muted">{label}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
};
