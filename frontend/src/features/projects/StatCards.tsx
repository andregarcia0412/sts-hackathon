import type { ComponentType, SVGProps } from "react";
import {
  CheckIcon,
  ErrorOutlineIcon,
  LightbulbIcon,
  SchemaIcon,
} from "@/components/icons/MaterialIcons";
import type { ProjectStatus } from "@/domain/types";

/* Static class names so Tailwind can see them */
const CARDS: {
  status: ProjectStatus | null;
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  circle: string;
}[] = [
  { status: null, label: "Projetos", Icon: LightbulbIcon, circle: "bg-card-orange/25 text-card-orange-strong" },
  { status: "ready", label: "Em análise", Icon: SchemaIcon, circle: "bg-card-blue text-white" },
  { status: "decided", label: "Decididos", Icon: CheckIcon, circle: "bg-card-green text-white" },
  { status: "processing", label: "Processando", Icon: ErrorOutlineIcon, circle: "bg-fg-subtle text-white" },
  { status: "error", label: "Com erro", Icon: ErrorOutlineIcon, circle: "bg-action text-white" },
];

interface StatCardsProps {
  counts: Record<ProjectStatus, number>;
  /** Status filter currently applied (one status at a time) */
  selected: ProjectStatus[];
  onSelect: (statuses: ProjectStatus[]) => void;
}

/** How many projects there are in each situation; each card is also the status filter */
export const StatCards = ({ counts, selected, onSelect }: StatCardsProps) => {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <div role="group" aria-label="Filtrar por situação" className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {CARDS.map(({ status, label, Icon, circle }) => {
        const count = status ? counts[status] : total;
        const active = status ? selected.length === 1 && selected[0] === status : selected.length === 0;
        return (
          <button
            key={label}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(status && !active ? [status] : [])}
            className={`group flex items-start justify-between rounded-2xl border-2 bg-surface p-4 text-left shadow-card transition-[translate,scale,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card-accent active:translate-y-0 active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 ${
              active ? "border-action shadow-card-accent" : "border-transparent hover:border-border-strong"
            }`}
          >
            <span className="flex flex-col gap-2">
              <span className="text-base text-fg-subtle">{label}</span>
              <span className="text-[32px] leading-none font-semibold text-fg tabular-nums">{count}</span>
            </span>
            <span
              className={`flex size-10 shrink-0 items-center justify-center rounded-full transition-transform duration-200 group-hover:scale-110 group-aria-pressed:scale-110 motion-reduce:transition-none ${circle}`}
            >
              <Icon className="size-6" />
            </span>
          </button>
        );
      })}
    </div>
  );
};
