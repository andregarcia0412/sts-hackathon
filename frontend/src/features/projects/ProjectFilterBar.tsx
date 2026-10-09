import { ListFilter } from "lucide-react";
import { PillSelect } from "@/components/ui/PillSelect";
import { DECISION_OUTCOMES, DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { SCORE_BAND_LABELS, SCORE_BANDS } from "@/domain/score";
import type { ProjectSort } from "@/domain/types";
import { DateRangeField } from "@/features/projects/DateRangeField";
import type { ProjectFilters } from "@/features/projects/useProjectFilters";

const SORT_LABELS: Record<ProjectSort, string> = {
  recent: "Mais recentes",
  oldest: "Mais antigos",
  name: "Nome (A–Z)",
  weakest: "Mais fraco primeiro",
};


interface ProjectFilterBarProps {
  filters: ProjectFilters;
  update: (patch: Partial<ProjectFilters>) => void;
  clear: () => void;
  activeCount: number;
}

/** Triage filters in one pill bar; the round button shows how many are on and clears them */
export const ProjectFilterBar = ({ filters, update, clear, activeCount }: ProjectFilterBarProps) => (
  <div role="group" aria-label="Filtros" className="flex flex-wrap items-center gap-2 rounded-[28px] bg-surface p-2 lg:rounded-full">
    <button
      type="button"
      onClick={clear}
      disabled={activeCount === 0}
      title={activeCount ? "Limpar filtros" : "Nenhum filtro ativo"}
      aria-label={activeCount ? `Limpar ${activeCount} ${activeCount === 1 ? "filtro" : "filtros"}` : "Nenhum filtro ativo"}
      className="relative flex size-12 shrink-0 items-center justify-center rounded-full bg-action text-white transition-[filter] hover:brightness-95 disabled:cursor-default disabled:hover:brightness-100"
    >
      <ListFilter className="size-5" aria-hidden />
      {activeCount > 0 && (
        <span className="absolute -top-1 -right-1 flex size-5 items-center justify-center rounded-full border-2 border-surface bg-brand-deep text-[11px] font-bold">
          {activeCount}
        </span>
      )}
    </button>

    <PillSelect
      label="Força da evidência do critério mais fraco"
      placeholder="Critério mais fraco"
      className="w-full sm:w-auto"
      highlighted={!!filters.weakestBand}
      value={filters.weakestBand}
      onChange={(weakestBand) => update({ weakestBand })}
      options={SCORE_BANDS.map((band) => ({
        value: band,
        label: `Mais fraco: ${SCORE_BAND_LABELS[band].toLowerCase()}`,
      }))}
    />

    <PillSelect
      label="Decisão"
      placeholder="Decisão"
      className="w-full sm:w-auto"
      highlighted={!!filters.outcome}
      value={filters.outcome}
      onChange={(outcome) => update({ outcome })}
      options={[
        ...DECISION_OUTCOMES.map((outcome) => ({ value: outcome, label: DECISION_OUTCOME_LABELS[outcome] })),
        { value: "none" as const, label: "Sem decisão" },
      ]}
    />

    <DateRangeField from={filters.from} to={filters.to} onChange={(range) => update(range)} />

    <PillSelect
      label="Ordenar por"
      className="w-full sm:w-auto"
      value={filters.sort}
      onChange={(sort) => update({ sort: sort ?? "recent", page: filters.page })}
      display={(option) => `Ordenar: ${option.label.toLowerCase()}`}
      options={(Object.keys(SORT_LABELS) as ProjectSort[]).map((sort) => ({ value: sort, label: SORT_LABELS[sort] }))}
    />
  </div>
);
