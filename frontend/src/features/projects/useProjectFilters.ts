import { useSearchParams } from "react-router-dom";
import type {
  DecisionOutcome,
  ProjectQuery,
  ProjectSort,
  ProjectStatus,
} from "@/domain/types";

export const PAGE_SIZE = 20;

/** Filters editable in the UI (owner and page size come from elsewhere) */
export type ProjectFilters = Omit<ProjectQuery, "ownerId" | "pageSize">;

const STATUSES: ProjectStatus[] = ["processing", "ready", "decided", "error"];
const BANDS = ["strong", "moderate", "weak"] as const;
const OUTCOMES: (DecisionOutcome | "none")[] = ["eligible", "not_eligible", "needs_review", "none"];
const SORTS: ProjectSort[] = ["recent", "oldest", "name", "weakest"];

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]) =>
  allowed.includes(value as T) ? (value as T) : undefined;

const DATE = /^\d{4}-\d{2}-\d{2}$/;

const parseFilters = (params: URLSearchParams): ProjectFilters => ({
  search: params.get("q") ?? undefined,
  statuses: (params.get("status") ?? "")
    .split(",")
    .map((s) => oneOf(s, STATUSES))
    .filter((s): s is ProjectStatus => !!s),
  weakestBand: oneOf(params.get("banda"), BANDS),
  outcome: oneOf(params.get("decisao"), OUTCOMES),
  from: DATE.test(params.get("de") ?? "") ? params.get("de")! : undefined,
  to: DATE.test(params.get("ate") ?? "") ? params.get("ate")! : undefined,
  sort: oneOf(params.get("ordem"), SORTS) ?? "recent",
  page: Math.max(1, Number(params.get("pagina")) || 1),
});

const serializeFilters = (filters: ProjectFilters) => {
  const entries: [string, string | undefined][] = [
    ["q", filters.search?.trim() || undefined],
    ["status", filters.statuses?.length ? filters.statuses.join(",") : undefined],
    ["banda", filters.weakestBand],
    ["decisao", filters.outcome],
    ["de", filters.from],
    ["ate", filters.to],
    ["ordem", filters.sort !== "recent" ? filters.sort : undefined],
    ["pagina", filters.page > 1 ? String(filters.page) : undefined],
  ];
  return new URLSearchParams(entries.filter((e): e is [string, string] => !!e[1]));
};

/**
 * Project list filters live in the URL (?q=&status=&banda=&decisao=&de=&ate=&ordem=&pagina=),
 * so a filtered list can be shared and the back button works.
 */
export const useProjectFilters = () => {
  const [params, setParams] = useSearchParams();
  const filters = parseFilters(params);

  /**
   * Changing any filter goes back to page 1, unless the page itself changes.
   * Reads the live URL, not the last render: React Router applies navigations
   * in a transition, so two quick changes would otherwise overwrite each other.
   */
  const update = (patch: Partial<ProjectFilters>) =>
    setParams(
      serializeFilters({
        ...parseFilters(new URLSearchParams(window.location.search)),
        page: 1,
        ...patch,
      }),
      // Typing in the search box should not flood the history
      { replace: "search" in patch },
    );

  const activeCount = [
    filters.search,
    filters.statuses?.length,
    filters.weakestBand,
    filters.outcome,
    filters.from,
    filters.to,
  ].filter(Boolean).length;

  const clear = () => setParams(new URLSearchParams());

  return { filters, update, clear, activeCount };
};
