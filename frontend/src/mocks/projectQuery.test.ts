import { describe, expect, it } from "vitest";
import type { ProjectQuery, ProjectSummary } from "@/domain/types";
import { applyProjectQuery } from "@/mocks/projectQuery";
import { GENERATED_COUNT, generatedProjects, synthesizeAnalyses } from "@/mocks/generatedProjects";

const project = (overrides: Partial<ProjectSummary>): ProjectSummary => ({
  id: "x",
  ownerId: "u1",
  name: "Projeto",
  createdAt: "2026-01-10T12:00:00.000Z",
  status: "ready",
  documents: [],
  ...overrides,
});

const scores = (...values: number[]) =>
  values.map((score, i) => ({ criterionKey: `k${i}`, name: `C${i}`, score }));

const all: ProjectSummary[] = [
  project({ id: "a", name: "Água potável", company: "Sertão Bio", createdAt: "2026-03-01T00:00:00Z", scoreSummary: scores(80, 30) }),
  project({ id: "b", name: "Bateria de sódio", createdAt: "2026-01-01T00:00:00Z", status: "decided", scoreSummary: scores(70, 75), lastDecision: { outcome: "eligible", decidedAt: "2026-01-05T00:00:00Z", analystName: "Ana" } }),
  project({ id: "c", name: "Cacau", createdAt: "2026-02-01T00:00:00Z", status: "processing" }),
  project({ id: "d", ownerId: "u2", name: "De outro analista" }),
];

const query = (overrides: Partial<ProjectQuery> = {}): ProjectQuery => ({
  ownerId: "u1",
  sort: "recent",
  page: 1,
  pageSize: 20,
  ...overrides,
});

const ids = (q: Partial<ProjectQuery>) => applyProjectQuery(all, query(q)).items.map((p) => p.id);

describe("applyProjectQuery", () => {
  it("only returns the analyst's own projects, newest first", () => {
    expect(ids({})).toEqual(["a", "c", "b"]);
  });

  it("counts statuses of the analyst's projects regardless of filters", () => {
    expect(applyProjectQuery(all, query({ search: "cacau" })).statusCounts).toEqual({
      processing: 1,
      ready: 1,
      decided: 1,
      error: 0,
    });
  });

  it("searches name and company ignoring accents and case", () => {
    expect(ids({ search: "agua" })).toEqual(["a"]);
    expect(ids({ search: "SERTAO" })).toEqual(["a"]);
  });

  it("filters by status, weakest band, decision and date range", () => {
    expect(ids({ statuses: ["processing", "decided"] })).toEqual(["c", "b"]);
    expect(ids({ weakestBand: "weak" })).toEqual(["a"]);
    expect(ids({ weakestBand: "strong" })).toEqual(["b"]);
    expect(ids({ outcome: "eligible" })).toEqual(["b"]);
    expect(ids({ outcome: "none" })).toEqual(["a", "c"]);
    expect(ids({ from: "2026-01-15", to: "2026-02-28" })).toEqual(["c"]);
  });

  it("sorts by weakest score (unanalysed last) and by name", () => {
    expect(ids({ sort: "weakest" })).toEqual(["a", "b", "c"]);
    expect(ids({ sort: "name" })).toEqual(["a", "b", "c"]);
  });

  it("paginates and clamps the page", () => {
    const page = applyProjectQuery(all, query({ pageSize: 2, page: 9 }));
    expect(page).toMatchObject({ page: 2, total: 3 });
    expect(page.items.map((p) => p.id)).toEqual(["b"]);
  });
});

describe("generatedProjects", () => {
  it("is deterministic and spread over the demo analysts", () => {
    const projects = generatedProjects();
    expect(projects).toHaveLength(GENERATED_COUNT);
    expect(new Set(projects.map((g) => g.project.ownerId)).size).toBe(3);
    expect(projects[0].project.name).toBe(generatedProjects()[0].project.name);
  });

  it("never dates a decision before its project or after the demo's 'today'", () => {
    for (const g of generatedProjects()) {
      if (!g.decision) continue;
      expect(g.decision.decidedAt >= g.project.createdAt).toBe(true);
      expect(g.decision.decidedAt <= "2026-10-07").toBe(true);
    }
  });

  it("gives decided projects a decision and analysed projects consistent scores", () => {
    for (const g of generatedProjects().slice(0, 50)) {
      expect(!!g.decision).toBe(g.project.status === "decided");
      const analyses = synthesizeAnalyses(g);
      if (g.project.status === "ready" || g.project.status === "decided") {
        expect(analyses[0].criteria.map((c) => c.score)).toEqual(g.scores[0]);
      } else {
        expect(analyses).toEqual([]);
      }
    }
  });
});
