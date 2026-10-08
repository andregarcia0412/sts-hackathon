import { ListFilter } from "lucide-react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { SCORE_BAND_LABELS, SCORE_BANDS } from "@/domain/score";
import type { DecisionOutcome, ProjectSort } from "@/domain/types";
import { DateRangeField } from "@/features/projects/DateRangeField";
import type { ProjectFilters } from "@/features/projects/useProjectFilters";

const SORT_LABELS: Record<ProjectSort, string> = {
  recent: "Mais recentes",
  oldest: "Mais antigos",
  name: "Nome (A–Z)",
  weakest: "Critério mais fraco primeiro",
};

const OUTCOMES: DecisionOutcome[] = ["eligible", "with_reservations", "not_eligible"];

/*
 * Pill select of the design; highlighted when it filters something. Each width
 * fits its longest option (a chosen option is never cut).
 */
const pillSelect = (active: boolean, width = "sm:w-48") =>
  `select h-12 w-full rounded-full py-0 pr-10 pl-4 text-base ${width} ${active ? "border-action" : ""}`;

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

    <select
      aria-label="Força da evidência do critério mais fraco"
      className={pillSelect(!!filters.weakestBand, "sm:w-72")}
      value={filters.weakestBand ?? ""}
      onChange={(e) => update({ weakestBand: (e.target.value || undefined) as ProjectFilters["weakestBand"] })}
    >
      <option value="">Critério mais fraco</option>
      {SCORE_BANDS.map((band) => (
        <option key={band} value={band}>
          Mais fraco: {SCORE_BAND_LABELS[band].toLowerCase()}
        </option>
      ))}
    </select>

    <select
      aria-label="Decisão"
      className={pillSelect(!!filters.outcome)}
      value={filters.outcome ?? ""}
      onChange={(e) => update({ outcome: (e.target.value || undefined) as ProjectFilters["outcome"] })}
    >
      <option value="">Decisão</option>
      {OUTCOMES.map((outcome) => (
        <option key={outcome} value={outcome}>
          {DECISION_OUTCOME_LABELS[outcome]}
        </option>
      ))}
      <option value="none">Sem decisão</option>
    </select>

    <DateRangeField from={filters.from} to={filters.to} onChange={(range) => update(range)} />

    <select
      aria-label="Ordenar por"
      className={pillSelect(false, "sm:w-64")}
      value={filters.sort}
      onChange={(e) => update({ sort: e.target.value as ProjectSort, page: filters.page })}
    >
      {(Object.keys(SORT_LABELS) as ProjectSort[]).map((sort) => (
        <option key={sort} value={sort}>
          {sort === "recent" ? "Ordenar: mais recentes" : SORT_LABELS[sort]}
        </option>
      ))}
    </select>
  </div>
);
