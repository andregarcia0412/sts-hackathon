import { projectCode } from "@/domain/projects";
import { scoreBand } from "@/domain/score";
import type {
  ProjectPage,
  ProjectQuery,
  ProjectStatus,
  ProjectSummary,
} from "@/domain/types";

/*
 * MOCK of what the back-end will do in the database: filter, sort and
 * paginate the project list of one analyst.
 */

const normalize = (text: string) =>
  text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

/** Lowest criterion score of the primary method, if analysed */
export const weakestScore = (project: ProjectSummary) =>
  project.scoreSummary?.length
    ? Math.min(...project.scoreSummary.map((s) => s.score))
    : undefined;

const STATUSES: ProjectStatus[] = ["processing", "ready", "decided", "error"];

const byName = new Intl.Collator("pt-BR", { sensitivity: "base" });

export const applyProjectQuery = (
  all: ProjectSummary[],
  query: ProjectQuery,
): ProjectPage => {
  const owned = all.filter((p) => p.ownerId === query.ownerId);
  const statusCounts = Object.fromEntries(
    STATUSES.map((status) => [status, owned.filter((p) => p.status === status).length]),
  ) as Record<ProjectStatus, number>;

  const search = query.search ? normalize(query.search.trim()) : "";
  const matches = owned.filter((p) => {
    const haystack = `${p.name} ${p.company ?? ""} projeto ${projectCode(p.id)}`;
    if (search && !normalize(haystack).includes(search)) return false;
    if (query.statuses?.length && !query.statuses.includes(p.status)) return false;
    if (query.weakestBand) {
      const weakest = weakestScore(p);
      if (weakest === undefined || scoreBand(weakest) !== query.weakestBand) return false;
    }
    if (query.outcome === "none" && p.lastDecision) return false;
    if (query.outcome && query.outcome !== "none" && p.lastDecision?.outcome !== query.outcome) {
      return false;
    }
    const day = p.createdAt.slice(0, 10);
    if (query.from && day < query.from) return false;
    if (query.to && day > query.to) return false;
    return true;
  });

  const sorted = [...matches].sort((a, b) => {
    switch (query.sort) {
      case "oldest":
        return a.createdAt.localeCompare(b.createdAt);
      case "name":
        return byName.compare(a.name, b.name);
      case "weakest":
        return (weakestScore(a) ?? Infinity) - (weakestScore(b) ?? Infinity);
      default:
        return b.createdAt.localeCompare(a.createdAt);
    }
  });

  const pageCount = Math.max(1, Math.ceil(sorted.length / query.pageSize));
  const page = Math.min(Math.max(1, query.page), pageCount);
  return {
    items: sorted.slice((page - 1) * query.pageSize, page * query.pageSize),
    total: sorted.length,
    page,
    pageSize: query.pageSize,
    statusCounts,
  };
};
