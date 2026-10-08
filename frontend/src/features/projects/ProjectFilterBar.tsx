import { Search, X } from "lucide-react";
import { useEffect, useEffectEvent, useState } from "react";
import { DECISION_OUTCOME_LABELS } from "@/domain/labels";
import { BAND_CRITERION_STATUS, CRITERION_STATUS } from "@/domain/qualitative";
import { SCORE_BANDS } from "@/domain/score";
import type { DecisionOutcome, ProjectSort } from "@/domain/types";
import type { ProjectFilters } from "@/features/projects/useProjectFilters";

const SEARCH_DEBOUNCE_MS = 300;

const SORT_LABELS: Record<ProjectSort, string> = {
  recent: "Mais recentes",
  oldest: "Mais antigos",
  name: "Nome (A–Z)",
  weakest: "Critério mais fraco primeiro",
};

interface ProjectFilterBarProps {
  filters: ProjectFilters;
  update: (patch: Partial<ProjectFilters>) => void;
  clear: () => void;
  activeCount: number;
}

/** All filters in one row above the list (wraps on small screens) */
export const ProjectFilterBar = ({ filters, update, clear, activeCount }: ProjectFilterBarProps) => {
  const [search, setSearch] = useState(filters.search ?? "");

  // Debounced: the URL (and the request) only change when typing pauses
  const onTypingPause = useEffectEvent(() => {
    if (search !== (filters.search ?? "")) update({ search });
  });
  useEffect(() => {
    const timer = setTimeout(onTypingPause, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search]);

  return (
    <div role="search" aria-label="Filtrar projetos" className="card flex flex-wrap items-end gap-3 p-4">
      <div className="min-w-56 flex-1">
        <label htmlFor="filter-search" className="field-label">
          Buscar
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-fg-muted" aria-hidden />
          <input
            id="filter-search"
            type="search"
            className="input pl-11"
            placeholder="Projeto ou empresa"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div>
        <label htmlFor="filter-band" className="field-label">
          Critério mais fraco
        </label>
        <select
          id="filter-band"
          className="select w-auto"
          value={filters.weakestBand ?? ""}
          onChange={(e) =>
            update({ weakestBand: (e.target.value || undefined) as ProjectFilters["weakestBand"] })
          }
        >
          <option value="">Qualquer</option>
          {SCORE_BANDS.map((band) => (
            <option key={band} value={band}>
              {CRITERION_STATUS[BAND_CRITERION_STATUS[band]].label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-outcome" className="field-label">
          Decisão
        </label>
        <select
          id="filter-outcome"
          className="select w-auto"
          value={filters.outcome ?? ""}
          onChange={(e) =>
            update({ outcome: (e.target.value || undefined) as DecisionOutcome | "none" | undefined })
          }
        >
          <option value="">Qualquer</option>
          {(Object.keys(DECISION_OUTCOME_LABELS) as DecisionOutcome[]).map((outcome) => (
            <option key={outcome} value={outcome}>{DECISION_OUTCOME_LABELS[outcome]}</option>
          ))}
          <option value="none">Sem decisão</option>
        </select>
      </div>

      <fieldset className="flex items-end gap-1.5">
        <legend className="field-label">Enviado entre</legend>
        <input
          type="date"
          aria-label="Enviado a partir de"
          className="input w-auto"
          value={filters.from ?? ""}
          max={filters.to}
          onChange={(e) => update({ from: e.target.value || undefined })}
        />
        <span className="pb-3.5 text-xs text-fg-muted">e</span>
        <input
          type="date"
          aria-label="Enviado até"
          className="input w-auto"
          value={filters.to ?? ""}
          min={filters.from}
          onChange={(e) => update({ to: e.target.value || undefined })}
        />
      </fieldset>

      <div>
        <label htmlFor="filter-sort" className="field-label">
          Ordenar por
        </label>
        <select
          id="filter-sort"
          className="select w-auto"
          value={filters.sort}
          onChange={(e) => update({ sort: e.target.value as ProjectSort, page: filters.page })}
        >
          {(Object.keys(SORT_LABELS) as ProjectSort[]).map((sort) => (
            <option key={sort} value={sort}>{SORT_LABELS[sort]}</option>
          ))}
        </select>
      </div>

      {activeCount > 0 && (
        <button
          type="button"
          className="btn-ghost mb-1.5"
          onClick={() => {
            setSearch("");
            clear();
          }}
        >
          <X className="size-4" aria-hidden />
          Limpar filtros ({activeCount})
        </button>
      )}
    </div>
  );
};
