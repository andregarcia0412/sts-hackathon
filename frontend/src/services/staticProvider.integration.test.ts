/*
 * Integration proof (spec 14 E1, G4): the REAL export (backend-export-frontend
 * output, PRJ90 analysed by the real pipeline, 228-node graph). Fixtures under
 * __fixtures__/static-api/ are a verbatim copy of static-api/ — confidential
 * (excerpts of the challenge package), so the folder is gitignored: a fresh
 * checkout has none and the suite skips this file (the provider itself is
 * fully covered by staticProvider.test.ts against the hand-made fixture).
 *
 * Refresh after `uv run backend-export-frontend`:
 *   rm -rf src/services/__fixtures__/static-api && cp -r static-api src/services/__fixtures__/static-api
 */

import { describe, expect, it } from "vitest";

// Glob instead of static imports: an absent folder yields {} instead of a module-not-found error
const files = import.meta.glob<unknown>("./__fixtures__/static-api/**/*.json", { eager: true, import: "default" });
const analysesEntry = Object.entries(files).find(([path]) => path.endsWith("/analyses.json"));
const projectDir = analysesEntry?.[0].slice(0, -"/analyses.json".length);
const graphEntry = Object.entries(files).find(
  ([path]) => projectDir && path.startsWith(`${projectDir}/analysis/`) && path.endsWith("/graph.json"),
);

const page = files["./__fixtures__/static-api/projects.json"] as
  | { total: number; items: { scoreSummary?: { score: number }[] }[] }
  | undefined;
const analyses = (analysesEntry?.[1] ?? null) as { id: string; criteria: unknown[] }[] | null;
const graph = (graphEntry?.[1] ?? { nodes: [], edges: [] }) as { nodes: unknown[]; edges: unknown[] };

describe("static export × real pipeline data", () => {
  it.skipIf(!page || !analyses)("carries the analysed project through every route shape", () => {
    // the list knows the five criterion scores
    const ready = page!.items.find((i) => i.scoreSummary?.length === 5);
    expect(ready).toBeDefined();

    // the tree has the five criteria and the pipeline's suggestion
    expect(analyses).toHaveLength(1);
    expect(analyses![0].criteria).toHaveLength(5);

    // the graph is the full evidence graph the API would answer
    expect(graph.nodes.length).toBeGreaterThan(50);
    expect(graph.edges.length).toBeGreaterThan(50);
  });
});