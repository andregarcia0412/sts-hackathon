import { CircleAlert, CircleCheckBig, FolderOpen, LoaderCircle, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { TONE_STYLES } from "@/components/ui/toneStyles";
import { PROJECT_STATUS_LABELS, PROJECT_STATUS_TONES } from "@/domain/labels";
import type { Tone } from "@/domain/qualitative";
import type { ProjectStatus } from "@/domain/types";

const TILES: { status: ProjectStatus | null; label: string; Icon: LucideIcon; tone: Tone }[] = [
  { status: null, label: "Todos", Icon: FolderOpen, tone: "neutral" },
  { status: "ready", label: PROJECT_STATUS_LABELS.ready, Icon: Search, tone: PROJECT_STATUS_TONES.ready },
  { status: "decided", label: "Decididos", Icon: CircleCheckBig, tone: PROJECT_STATUS_TONES.decided },
  { status: "processing", label: PROJECT_STATUS_LABELS.processing, Icon: LoaderCircle, tone: PROJECT_STATUS_TONES.processing },
  { status: "error", label: "Com erro", Icon: CircleAlert, tone: PROJECT_STATUS_TONES.error },
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
    <ul aria-label="Resumo dos meus projetos" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {TILES.map(({ status, label, Icon, tone }) => {
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
              className={`flex w-full items-center gap-3 rounded-2xl p-3 text-left transition-colors ${
                active
                  ? "border-2 border-action bg-surface"
                  : "border-2 border-transparent bg-white/80 hover:border-border-strong"
              }`}
            >
              <span
                className={`flex size-10 shrink-0 items-center justify-center rounded-full ${TONE_STYLES[tone].soft} ${TONE_STYLES[tone].icon}`}
              >
                <Icon className="size-5" aria-hidden />
              </span>
              <span className="min-w-0">
                <span className="block text-2xl leading-7 font-semibold tabular-nums">{value}</span>
                <span className="block truncate text-xs leading-4 text-fg-muted">{label}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
};
