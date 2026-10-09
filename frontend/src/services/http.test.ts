/*
 * HTTP layer (spec 14 E2/E3): the real API client — Bearer token, one refresh
 * attempt on 401, timeout, and the writes (upload multipart, decisions,
 * contestations, reanalysis, assistant). Pure-node vitest with stubbed fetch.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ProjectQuery } from "@/domain/types";

const stubBrowserGlobals = () => {
  const store = new Map<string, string>();
  vi.stubGlobal("window", {});
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  });
  vi.stubGlobal("crypto", { randomUUID: () => "test-uuid-0002" });
};

const TOKENS = { access_token: "at-1", refresh_token: "rt-1", token_type: "bearer" };

describe("http + api in api mode (spec 14 E2/E3)", () => {
  beforeEach(() => {
    vi.resetModules();
    stubBrowserGlobals();
    vi.stubEnv("VITE_DATA_SOURCE", "api");
    vi.stubEnv("VITE_API_URL", "http://api.test");
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  const loadApi = async () => import("@/services/api");
  const fetchCalls = () => (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls as [string, unknown][];
  const json = (status: number, body: unknown) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  const loggedInApi = async (fetchMock: ReturnType<typeof vi.fn>) => {
    vi.stubGlobal("fetch", fetchMock);
    const api = await loadApi();
    await api.login("user1@sts.com", "senha12345");
    return api;
  };

  it("login exchanges credentials for tokens and persists the session", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(200, TOKENS)));
    expect(fetchCalls()[0][0]).toContain("/auth/login");
    expect(localStorage.getItem("lei-do-bem:tokens")).toContain("at-1");
    expect(api.dataSourceLabel()).toMatch(/api/i);
  });

  it("sends the Bearer token and refreshes exactly once on 401", async () => {
    let projectCalls = 0;
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/login")) return Promise.resolve(json(200, TOKENS));
      if (url.includes("/auth/refresh")) return Promise.resolve(json(200, TOKENS));
      projectCalls += 1;
      return Promise.resolve(
        json(projectCalls === 1 ? 401 : 200, { items: [], total: 0, page: 1, pageSize: 20, statusCounts: {} }),
      );
    });
    const api = await loggedInApi(fetchMock);
    const page = await api.listProjects({ ownerId: "u1", sort: "recent", page: 1, pageSize: 20 } as ProjectQuery);
    expect(page.total).toBe(0);
    expect(fetchCalls().filter(([u]) => (u as string).includes("/auth/refresh"))).toHaveLength(1); // one refresh, no loop
    const projectCall = fetchCalls().find(([u]) => (u as string).includes("/projects"))!;
    expect((projectCall[1] as { headers: Headers }).headers.get("Authorization")).toBe("Bearer at-1");
  });

  it("falls back to the mock when the API is unreachable (demo never breaks)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const api = await loadApi();
    const page = await api.listProjects({ ownerId: "u1", sort: "recent", page: 1, pageSize: 20 } as ProjectQuery);
    expect(page.items.length).toBeGreaterThan(0); // the ~400 mock projects answer instead
  });

  it("maps the backend's outcomes to the front's vocabulary when saving a decision", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(201, {
      projectId: "p1", analysisId: "a1", outcome: "eligible_with_caveats",
      justification: "sem elo", analystName: "Ana", decidedAt: "2026-10-09T15:00:00Z",
    })));
    const saved = await api.saveDecision({
      projectId: "p1", analysisId: "a1", outcome: "with_reservations", justification: "com limitação", analystName: "Ana",
    });
    const decisionCall = fetchCalls().find(([u]) => (u as string).includes("/decisions"))!;
    expect(JSON.parse((decisionCall[1] as { body: string }).body))
      .toMatchObject({ outcome: "eligible_with_caveats" }); // mapped to the backend's vocabulary
    expect(saved.outcome).toBe("with_reservations"); // the front keeps its vocabulary
  });

  it("uploads the package as multipart and returns the created project", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(201, {
      id: "p2", ownerId: "u1", name: "Novo", createdAt: "2026-10-09T15:00:00Z",
      status: "processing", documents: [],
    })));
    const file = new File([" conteudo "], "dossie.pdf", { type: "application/pdf" });
    const project = await api.createProject({ name: "Novo", files: [file], webSearch: false }, "u1");
    const uploadCall = fetchCalls().find(([u]) => (u as string).endsWith("/projects"))!;
    expect((uploadCall[1] as { method: string }).method).toBe("POST");
    expect((uploadCall[1] as { body: FormData }).body).toBeInstanceOf(FormData); // multipart, not JSON
    expect(project.id).toBe("p2");
  });

  it("asks the assistant over POST /assistant/ask", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(200, {
      blocks: [{ type: "text", text: "resposta" }], sources: [], suggestions: [],
    })));
    const answer = await api.askAssistant("o que é novidade?", {
      screen: "analysis", analysis: {} as never, selectedNodeId: null,
    });
    expect(answer.blocks[0]).toEqual({ type: "text", text: "resposta" });
  });

  /* The back-end only produces Frascati: the front adds the illustrative MCTI example */
  const frascatiOnly = async () => {
    const { soilSensorAnalysis } = await import("@/mocks/analysis-soil-sensor");
    return [{ ...soilSensorAnalysis, id: "real-analysis", projectId: "real-project" }];
  };

  it("adds the illustrative MCTI analysis next to the back-end's Frascati", async () => {
    const analyses = await frascatiOnly();
    const api = await loggedInApi(vi.fn().mockImplementation((url: string) =>
      Promise.resolve(url.includes("/auth/login") ? json(200, TOKENS) : json(200, analyses))));
    const shown = await api.getAnalyses("real-project");
    expect(shown?.map((a) => a.framework)).toEqual(["frascati", "mcti_form"]);
    expect(shown?.[1]).toMatchObject({ illustrative: true, projectId: "real-project" });
  });

  it("reads the analyst's records back from the API, outcomes in the front's vocabulary", async () => {
    const api = await loggedInApi(vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/login")) return Promise.resolve(json(200, TOKENS));
      if (url.includes("/rule-decisions")) {
        return Promise.resolve(json(200, [{ id: "rd1", projectId: "real-project", analysisId: "real-analysis",
          nodeId: "crit-novelty.rule-proj-12", rating: "sustained", justification: "ok", author: "Ana",
          createdAt: "2026-10-09T15:00:00Z" }]));
      }
      return Promise.resolve(json(200, [{ projectId: "real-project", analysisId: "real-analysis",
        outcome: "eligible_with_caveats", justification: "x", analystName: "Ana", decidedAt: "2026-10-09T15:00:00Z" }]));
    }));
    expect((await api.listRuleDecisions("real-project")).map((d) => d.id)).toEqual(["rd1"]);
    expect((await api.listDecisions("real-project"))[0].outcome).toBe("with_reservations");
  });

  it("keeps what is recorded on the illustrative analysis in the browser", async () => {
    const analyses = await frascatiOnly();
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/auth/login")) return Promise.resolve(json(200, TOKENS));
      if (url.includes("/analyses")) return Promise.resolve(json(200, analyses));
      if (url.includes("/decisions") && !url.includes("rule")) return Promise.resolve(json(201, {
        projectId: "real-project", analysisId: "real-analysis", outcome: "eligible",
        justification: "x", analystName: "Ana", decidedAt: "2026-10-09T15:00:00Z" }));
      return Promise.resolve(json(200, []));
    });
    const api = await loggedInApi(fetchMock);
    const mcti = (await api.getAnalyses("real-project"))![1];

    const rating = await api.createRuleDecision({ projectId: "real-project", analysisId: mcti.id,
      nodeId: mcti.criteria[0].rules[0].id, rating: "sustained", justification: "ok", author: "Ana" } as never);
    expect(fetchCalls().some(([u, init]) => (u as string).includes("/rule-decisions") &&
      (init as { method?: string })?.method === "POST")).toBe(false);
    expect((await api.listRuleDecisions("real-project")).map((d) => d.id)).toContain(rating.id);

    await api.saveDecision({ projectId: "real-project", analysisId: "real-analysis",
      analysisIds: ["real-analysis", mcti.id], outcome: "eligible", justification: "x", analystName: "Ana",
      ruleOverrides: [{ ruleId: "r", note: "n", analysisId: mcti.id }] });
    const decisionCall = fetchCalls().find(([u, init]) => (u as string).endsWith("/decisions") &&
      (init as { method?: string })?.method === "POST")!;
    expect(JSON.parse((decisionCall[1] as { body: string }).body)).toMatchObject({
      analysisIds: ["real-analysis"], ruleOverrides: [] });
  });
});
