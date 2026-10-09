import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ProjectQuery } from "@/domain/types";

/* Pure-node vitest: stub what api.ts touches at import/DEV time (renewed per test). */

const stubBrowserGlobals = () => {
  const store = new Map<string, string>();
  vi.stubGlobal("window", { resetMockData: undefined });
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  });
  vi.stubGlobal("crypto", { randomUUID: () => "test-uuid-0001" });
};

describe("static provider (spec 14 E1)", () => {
  beforeEach(() => {
    vi.resetModules();
    stubBrowserGlobals();
    vi.stubEnv("VITE_DATA_SOURCE", "static");
    vi.stubEnv("VITE_STATIC_API_DIR", "src/services/__fixtures__/static-export");
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  const load = async () => {
    const api = await import("@/services/api");
    return api;
  };

  it("lists the exported projects with the real scoreSummary", async () => {
    const api = await load();
    const query: ProjectQuery = {
      ownerId: "user-1",
      sort: "recent",
      page: 1,
      pageSize: 20,
    };
    const page = await api.listProjects(query);
    expect(page.total).toBe(2);
    const ready = page.items.find((p) => p.id === "static-proj-1");
    expect(ready?.scoreSummary?.[0]).toEqual({
      criterionKey: "novelty",
      name: "Novidade",
      score: 80,
    });
    expect(ready?.frameworks).toEqual(["frascati"]);
  });

  it("applies the ProjectQuery filters locally over the exported list", async () => {
    const api = await load();
    const query: ProjectQuery = {
      ownerId: "user-1",
      statuses: ["processing"],
      sort: "recent",
      page: 1,
      pageSize: 20,
    };
    const page = await api.listProjects(query);
    expect(page.total).toBe(1);
    expect(page.items[0].id).toBe("static-proj-2");
  });

  it("returns the exported analysis tree with a null score for rule without evidence", async () => {
    const api = await load();
    const analyses = await api.getAnalyses("static-proj-1");
    expect(analyses).not.toBeNull();
    const novelty = analyses?.[0].criteria.find((c) => c.key === "novelty");
    const withEvidence = novelty?.rules.find((r) => r.score !== null);
    const withoutEvidence = novelty?.rules.find((r) => r.score === null);
    expect(withEvidence?.score).toBe(80);
    expect(withoutEvidence?.score).toBeNull(); // null = no evidence, never zero
  });

  it("returns null for a project without a finished analysis", async () => {
    const api = await load();
    const analyses = await api.getAnalyses("static-proj-2");
    expect(analyses).toBeNull();
  });

  it("reads decisions and contestations from the export", async () => {
    const api = await load();
    const decisions = await api.listDecisions("static-proj-1");
    expect(decisions).toHaveLength(1);
    expect(decisions[0].outcome).toBe("not_eligible");
    expect(decisions[0].decidedAt).toBe("2026-10-09T14:00:00.000Z");
    const contestations = await api.listContestations("static-proj-1");
    expect(contestations).toHaveLength(1);
    expect(contestations[0].status).toBe("open");
  });

  it("exposes the data source label for the banner", async () => {
    const api = await load();
    expect(api.dataSourceLabel()).toMatch(/estático/i);
    expect(api.dataSourceLabel()).not.toMatch(/fict/i);
  });

  it("serves the mock users when the export has none (login fallback)", async () => {
    vi.stubEnv("VITE_STATIC_API_DIR", "src/services/__fixtures__/no-export");
    const api = await load();
    const users = await api.listDemoUsers();
    expect(users.length).toBeGreaterThan(0);
    expect(users[0].id).toBeDefined();
  });

  it("keeps mutations on the mock path in static mode", async () => {
    const api = await load();
    const decision = await api.saveDecision({
      projectId: "static-proj-1",
      analysisId: "static-analysis-1",
      outcome: "eligible",
      justification: "decisão do analista",
      analystName: "Ana",
    });
    expect(decision.decidedAt).toBeDefined(); // mock answered, no fetch happened
    expect(decision.outcome).toBe("eligible");
  });

  it("defaults to the mock source when VITE_DATA_SOURCE is unset", async () => {
    vi.stubEnv("VITE_DATA_SOURCE", "");
    const api = await load();
    expect(api.dataSourceLabel()).toMatch(/fict/i);
  });
});