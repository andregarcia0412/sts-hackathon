/*
 * Integration proof (spec 14 E1, G4): the REAL export (backend-export-frontend
 * output, PRJ90 analysed by the real pipeline, 228-node graph). Fixtures under
 * __fixtures__/static-api/ are a verbatim copy of static-api/ — a fresh
 * checkout has none and the suite skips this file (the provider itself is
 * fully covered by staticProvider.test.ts against the hand-made fixture).
 *
 * Refresh after `uv run backend-export-frontend`:
 *   rm -rf src/services/__fixtures__/static-api && cp -r static-api src/services/__fixtures__/static-api
 */

import { describe, expect, it } from "vitest";
import realProjects from "@/services/__fixtures__/static-api/projects.json";
import realAnalyses from "@/services/__fixtures__/static-api/6ac8e74202341aeec65f9486/analyses.json";
import realGraph from "@/services/__fixtures__/static-api/6ac8e74202341aeec65f9486/analysis/6ac8e74202341aeec65f949b/graph.json";

const page = realProjects as { total: number; items: { scoreSummary?: { score: number }[] }[] };
const analyses = realAnalyses as { id: string; criteria: unknown[] }[] | null;
const graph = realGraph as { nodes: unknown[]; edges: unknown[] };

describe("static export × real pipeline data", () => {
  it.skipIf(!analyses)("carries the analysed project through every route shape", () => {
    // the list knows the five criterion scores
    const ready = page.items.find((i) => i.scoreSummary?.length === 5);
    expect(ready).toBeDefined();

    // the tree has the five criteria and the pipeline's suggestion
    expect(analyses).toHaveLength(1);
    expect(analyses![0].criteria).toHaveLength(5);

    // the graph is the full evidence graph the API would answer
    expect(graph.nodes.length).toBeGreaterThan(50);
    expect(graph.edges.length).toBeGreaterThan(50);
  });
});