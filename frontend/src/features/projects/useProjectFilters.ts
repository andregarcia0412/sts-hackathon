import { useSearchParams } from "react-router-dom";
import { paths } from "@/routes/paths";
import type { ProjectQuery, ProjectSort, ProjectStatus } from "@/domain/types";

export const PAGE_SIZE = 8;

/**
 * Filters editable in the UI (owner and page size come from elsewhere).
 * The status is the main filter; the API also takes outcome and dates, but the
 * screen keeps only what helps triage (team decision).
 */
export type ProjectFilters = Omit<ProjectQuery, "ownerId" | "pageSize" | "outcome" | "from" | "to">;

const STATUSES: ProjectStatus[] = ["processing", "ready", "decided", "error"];
const BANDS = ["strong", "moderate", "weak"] as const;
const SORTS: ProjectSort[] = ["recent", "oldest", "name", "weakest"];

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]) =>
  allowed.includes(value as T) ? (value as T) : undefined;

const parseFilters = (params: URLSearchParams): ProjectFilters => ({
  search: params.get("q") ?? undefined,
  statuses: (params.get("status") ?? "")
    .split(",")
    .map((s) => oneOf(s, STATUSES))
    .filter((s): s is ProjectStatus => !!s),
  weakestBand: oneOf(params.get("banda"), BANDS),
  sort: oneOf(params.get("ordem"), SORTS) ?? "recent",
  page: Math.max(1, Number(params.get("pagina")) || 1),
});

const serializeFilters = (filters: ProjectFilters) => {
  const entries: [string, string | undefined][] = [
    ["q", filters.search?.trim() || undefined],
    ["status", filters.statuses?.length ? filters.statuses.join(",") : undefined],
    ["banda", filters.weakestBand],
    ["ordem", filters.sort !== "recent" ? filters.sort : undefined],
    ["pagina", filters.page > 1 ? String(filters.page) : undefined],
  ];
  return new URLSearchParams(entries.filter((e): e is [string, string] => !!e[1]));
};

/**
 * Project list filters live in the URL (?q=&status=&banda=&ordem=&pagina=),
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
  const update = (patch: Partial<ProjectFilters>) => {
    // A late update (e.g. the debounced search) must not pull the analyst back
    // to the list after they already opened a project
    if (window.location.pathname !== paths.projects()) return;
    setParams(
      serializeFilters({
        ...parseFilters(new URLSearchParams(window.location.search)),
        page: 1,
        ...patch,
      }),
      // Typing in the search box should not flood the history
      { replace: "search" in patch },
    );
  };

  // The status tabs are the main filter, always visible: not counted here
  const activeCount = [filters.search, filters.weakestBand].filter(Boolean).length;

  const clear = () => setParams(new URLSearchParams());

  return { filters, update, clear, activeCount };
};
