/*
 * Static provider (spec 14 E1): reads the folder exported by
 * `uv run backend-export-frontend` — one JSON per API route — so the app can
 * run without the back-end. Read-only: mutations stay on the mock path.
 *
 * Loading: import.meta.glob in the build; fetch against the dev server in
 * development. The folder can be missing (empty page, null analyses) — that is
 * a valid state, not an error.
 */

import type {
  Analysis,
  Contestation,
  Decision,
  EvidenceReview,
  Project,
  ProjectPage,
  ProjectSummary,
  RuleDecision,
  User,
} from "@/domain/types";
import { staticApiDir } from "@/services/dataSource";
import { applyProjectQuery } from "@/mocks/projectQuery";
import type { ProjectQuery } from "@/domain/types";

/* Graph of the backend (GET /analyses/{id}/graph) — only what the panel shows. */
export interface GraphNode {
  nodeId: string;
  kind: string;
  label: string;
  props: Record<string, unknown>;
}
export interface GraphEdge {
  source: string;
  target: string;
  kind: string;
  props: Record<string, unknown>;
}
export interface StaticGraph {
  analysisId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

type Json = Record<string, unknown>;

let cache: Map<string, Json | null> | null = null;

/*
 * The build bundles the whole export folder via import.meta.glob (fixtures in
 * tests resolve through the same map). In dev, files outside the bundle are
 * fetched from the folder Vite serves (VITE_STATIC_API_DIR).
 */
const globbed = import.meta.glob(
  [
    "/src/services/__fixtures__/static-export/**/*.json",
    "/src/services/__fixtures__/static-api/**/*.json",
  ],
  { import: "default" },
) as Record<string, () => Promise<unknown>>;

async function readJson(path: string): Promise<Json | null> {
  if (!cache) cache = new Map();
  if (cache.has(path)) return cache.get(path) ?? null;
  let value: Json | null = null;
  // 1) the real export, as served by Vite (dev) or deployed beside the bundle (prod)
  if (typeof fetch === "function") {
    try {
      const response = await fetch(`${staticApiDir()}/${path}`);
      if (response.ok) value = (await response.json()) as Json;
    } catch {
      value = null; // no server (vitest): fall through to the bundled fixture
    }
  }
  // 2) hand-made fixture (tests; also the offline fallback of a fresh checkout)
  if (value === null) {
    const importer = globbed[`/src/services/__fixtures__/static-export/${path}`];
    if (importer) {
      try {
        value = (await importer()) as Json;
      } catch {
        value = null;
      }
    }
  }
  cache.set(path, value);
  return value;
}

function clearCache() {
  cache = null;
}

export const staticUsers = async (): Promise<User[] | null> => {
  const users = (await readJson("users.json")) as unknown as User[] | null;
  return Array.isArray(users) ? users : null;
};

export const staticProjects = async (): Promise<ProjectSummary[]> => {
  const page = (await readJson("projects.json")) as ProjectPage | null;
  return page?.items ?? [];
};

export const staticListProjects = async (query: ProjectQuery): Promise<ProjectPage> => {
  const summaries = await staticProjects();
  return applyProjectQuery(structuredClone(summaries), query);
};

export const staticGetProject = async (projectId: string): Promise<Project | null> => {
  const project = (await readJson(`${projectId}/project.json`)) as Project | null;
  return project && project.id ? structuredClone(project) : null;
};

export const staticGetAnalyses = async (projectId: string): Promise<Analysis[] | null> => {
  const analyses = (await readJson(`${projectId}/analyses.json`)) as Analysis[] | null;
  if (analyses === null) return null;
  if (!Array.isArray(analyses) || analyses.length === 0) return null;
  return structuredClone(analyses);
};

export const staticGraph = async (analysisId: string, projectId: string): Promise<StaticGraph | null> => {
  const graph = (await readJson(`${projectId}/analysis/${analysisId}/graph.json`)) as StaticGraph | null;
  return graph && graph.analysisId ? structuredClone(graph) : null;
};

export const staticDecisions = async (projectId: string): Promise<Decision[]> => {
  const rows = (await readJson(`${projectId}/decisions.json`)) as Decision[] | null;
  return rows ? structuredClone(rows) : [];
};

export const staticContestations = async (projectId: string): Promise<Contestation[]> => {
  const rows = (await readJson(`${projectId}/contestations.json`)) as Contestation[] | null;
  return rows ? structuredClone(rows) : [];
};

export const staticRuleDecisions = async (projectId: string): Promise<RuleDecision[]> => {
  const rows = (await readJson(`${projectId}/rule-decisions.json`)) as RuleDecision[] | null;
  return rows ? structuredClone(rows) : [];
};

export const staticEvidenceReviews = async (projectId: string): Promise<EvidenceReview[]> => {
  const rows = (await readJson(`${projectId}/evidence-reviews.json`)) as EvidenceReview[] | null;
  return rows ? structuredClone(rows) : [];
};

export { clearCache };