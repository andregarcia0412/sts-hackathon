import { X } from "lucide-react";
import { SCORE_BAND_LABELS, SCORE_BANDS } from "@/domain/score";
import type { ProjectSort } from "@/domain/types";
import type { ProjectFilters } from "@/features/projects/useProjectFilters";

const SORT_LABELS: Record<ProjectSort, string> = {
  recent: "Mais recentes",
  oldest: "Mais antigos",
  name: "Nome (A–Z)",
  weakest: "Critério mais fraco primeiro",
};

const selectClass =
  "h-10 cursor-pointer appearance-none rounded-full border border-border-strong bg-surface bg-no-repeat py-2 pr-9 pl-4 text-sm leading-5 [background-image:var(--select-arrow)] [background-position:right_10px_center] [background-size:20px] focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-action";

interface ListToolbarProps {
  filters: ProjectFilters;
  update: (patch: Partial<ProjectFilters>) => void;
  clear: () => void;
  activeCount: number;
}

/** Secondary filters for triage, at the top of the list card */
export const ListToolbar = ({ filters, update, clear, activeCount }: ListToolbarProps) => (
  <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2 border-b border-track px-6 py-3">
    {activeCount > 0 && (
      <button type="button" className="btn-ghost mr-auto" onClick={clear}>
        <X className="size-4" aria-hidden />
        Limpar filtros ({activeCount})
      </button>
    )}
    <label className="flex items-center gap-2 text-xs font-medium text-fg-muted">
      Força da evidência do critério mais fraco
      <select
        className={selectClass}
        value={filters.weakestBand ?? ""}
        onChange={(e) =>
          update({ weakestBand: (e.target.value || undefined) as ProjectFilters["weakestBand"] })
        }
      >
        <option value="">Qualquer</option>
        {SCORE_BANDS.map((band) => (
          <option key={band} value={band}>
            {SCORE_BAND_LABELS[band]}
          </option>
        ))}
      </select>
    </label>
    <label className="flex items-center gap-2 text-xs font-medium text-fg-muted">
      Ordenar por
      <select
        className={selectClass}
        value={filters.sort}
        onChange={(e) => update({ sort: e.target.value as ProjectSort, page: filters.page })}
      >
        {(Object.keys(SORT_LABELS) as ProjectSort[]).map((sort) => (
          <option key={sort} value={sort}>
            {SORT_LABELS[sort]}
          </option>
        ))}
      </select>
    </label>
  </div>
);
