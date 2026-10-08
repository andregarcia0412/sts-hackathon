import { PROJECT_STATUS_LABELS } from "@/domain/labels";
import type { ProjectStatus } from "@/domain/types";

const TABS: { status: ProjectStatus | null; label: string }[] = [
  { status: null, label: "Todos" },
  { status: "ready", label: PROJECT_STATUS_LABELS.ready },
  { status: "processing", label: PROJECT_STATUS_LABELS.processing },
  { status: "decided", label: "Decididos" },
  { status: "error", label: "Com erro" },
];

interface StatusTabsProps {
  counts: Record<ProjectStatus, number>;
  /** Status filter currently applied (one status at a time) */
  selected: ProjectStatus[];
  onSelect: (statuses: ProjectStatus[]) => void;
}

/** Main filter of the list: the project's status, with how many there are in each */
export const StatusTabs = ({ counts, selected, onSelect }: StatusTabsProps) => {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <div
      role="group"
      aria-label="Filtrar por situação"
      className="flex max-w-full gap-2 overflow-x-auto rounded-full bg-surface p-2"
    >
      {TABS.map(({ status, label }) => {
        const count = status ? counts[status] : total;
        const active = status ? selected.length === 1 && selected[0] === status : selected.length === 0;
        return (
          <button
            key={label}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(status ? [status] : [])}
            className={`shrink-0 rounded-full px-6 py-3 text-base leading-5 font-semibold whitespace-nowrap transition-colors ${
              active ? "bg-action text-white" : "text-fg hover:bg-surface-sunken"
            }`}
          >
            {label}{" "}
            <span
              className={`text-xs ${
                active ? "text-brand-blush" : status === "error" && count > 0 ? "text-action" : "text-fg-muted"
              }`}
            >
              ({count})
            </span>
          </button>
        );
      })}
    </div>
  );
};
