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

  it("maps the backend's 4 outcomes to the front's 3 when saving a decision", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(201, {
      projectId: "p1", analysisId: "a1", outcome: "insufficient_evidence",
      justification: "sem elo", analystName: "Ana", decidedAt: "2026-10-09T15:00:00Z",
    })));
    const saved = await api.saveDecision({
      projectId: "p1", analysisId: "a1", outcome: "needs_review", justification: "faltam dados", analystName: "Ana",
    });
    const decisionCall = fetchCalls().find(([u]) => (u as string).includes("/decisions"))!;
    expect(JSON.parse((decisionCall[1] as { body: string }).body))
      .toMatchObject({ outcome: "insufficient_evidence" }); // mapped to the backend's vocabulary
    expect(saved.outcome).toBe("needs_review"); // the front keeps its vocabulary
  });

  it("uploads the package as multipart and returns the created project", async () => {
    const api = await loggedInApi(vi.fn().mockResolvedValue(json(201, {
      id: "p2", ownerId: "u1", name: "Novo", createdAt: "2026-10-09T15:00:00Z",
      status: "processing", documents: [],
    })));
    const file = new File([" conteudo "], "dossie.pdf", { type: "application/pdf" });
    const project = await api.createProject({ name: "Novo", files: [file] }, "u1");
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
});