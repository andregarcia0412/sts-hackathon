import type {
  Analysis,
  Contestation,
  NewContestationInput,
  Decision,
  EvidenceReview,
  NewDecisionInput,
  NewEvidenceReviewInput,
  NewRuleDecisionInput,
  NewProjectInput,
  Project,
  ProjectPage,
  ProjectDocument,
  ProjectQuery,
  ProjectSummary,
  RuleDecision,
  User,
} from "@/domain/types";
import type { AssistantAnswer, AssistantContext } from "@/domain/assistant";
import { answerQuestion } from "@/mocks/assistantEngine";
import { debateOpening, debateReply } from "@/mocks/debateEngine";
import { generatedProjects, hashId, synthesizeAnalyses } from "@/mocks/generatedProjects";
import type { GeneratedProject } from "@/mocks/generatedProjects";
import { applyProjectQuery } from "@/mocks/projectQuery";
import { applyAdjustments, reanalyze } from "@/mocks/reanalysis";
import { withScoreExplanations } from "@/mocks/scoreExplanations";
import { mockUsers } from "@/mocks/users";
import { decisionCsvColumns, decisionCsvFileName, decisionCsvRow, toCsv } from "@/domain/decisionCsv";
import { recognizeDocumentKind } from "@/domain/documents";
import { sortByFramework } from "@/domain/frameworks";
import { pendenciesOf } from "@/domain/report";
import { decidedCriteriaCount } from "@/domain/reviews";
import {
  analysisTemplates,
  mockAnalyses,
  mockDecisions,
  mockProjects,
} from "@/mocks/projects";
import { dataSource, dataSourceLabel } from "@/services/dataSource";
import {
  staticContestations,
  staticDecisions,
  staticEvidenceReviews,
  staticGetAnalyses,
  staticGetProject,
  staticListProjects,
  staticRuleDecisions,
  staticUsers,
} from "@/services/staticProvider";
import {
  ApiError,
  apiJson,
  apiPost,
  apiPostForm,
  saveTokens,
} from "@/services/http";

export { dataSourceLabel };
export { ApiError };

/*
 * Service layer. Screens only talk to these functions.
 * For now everything is read from in-memory mocks with an artificial delay;
 * when the back-end exists, swap the bodies for fetch calls here.
 */

const LATENCY_MS = 400;
const MOCK_PROCESSING_MS = 5000;
const ASSISTANT_LATENCY_MS = 700;
const REANALYSIS_LATENCY_MS = 1500;

export class NotFoundError extends Error {
  constructor(what: string) {
    super(`${what} não encontrado(a)`);
    this.name = "NotFoundError";
  }
}

export class AuthError extends Error {
  constructor(message = "E-mail ou senha inválidos") {
    super(message);
    this.name = "AuthError";
  }
}

/*
 * Mock database, persisted in localStorage so a demo survives a page reload.
 * Call resetMockData() (e.g. from the console via window.resetMockData) to
 * start over from the fictitious examples.
 *
 * The ~400 generated projects are NOT stored: they are recreated identically
 * on every load. A generated project that changes (e.g. gets a decision) is
 * copied into db.projects, which then takes precedence.
 */
// Bump the version when src/mocks changes, or browsers keep the old copy
const STORAGE_KEY = "lei-do-bem:mock-db:v7";

interface MockDb {
  projects: Project[];
  analyses: Analysis[];
  decisions: Decision[];
  contestations: Contestation[];
  ruleDecisions: RuleDecision[];
  evidenceReviews: EvidenceReview[];
  /** Analysts created on the "Cadastro" tab (demo: no password is kept) */
  users: User[];
  /** Mock-created projects become "ready" after this timestamp (ms) */
  processingUntil: Record<string, number>;
}

const seedDb = (): MockDb => ({
  projects: structuredClone(mockProjects),
  analyses: structuredClone(mockAnalyses),
  decisions: structuredClone(mockDecisions),
  contestations: [],
  ruleDecisions: [],
  evidenceReviews: [],
  users: [],
  processingUntil: {},
});

const loadDb = (): MockDb => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    // Spread over the seed so fields added later get a default
    if (raw) return { ...seedDb(), ...(JSON.parse(raw) as Partial<MockDb>) };
  } catch {
    // Storage unavailable or corrupted: fall back to the seed
  }
  return seedDb();
};

let db = loadDb();

const persist = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // Non-essential: the demo still works in memory
  }
};

export const resetMockData = () => {
  db = seedDb();
  persist();
};

if (import.meta.env.DEV) {
  Object.assign(window, { resetMockData });
}

const toDocument = (file: File, uploadedAt: string): ProjectDocument => {
  // Dropped folders keep their relative path (react-dropzone): show it as the name
  const path = (file as File & { path?: string }).path?.replace(/^\.?\//, "");
  const fileName = path || file.name;
  return {
    id: newId("doc"),
    fileName,
    mimeType: file.type,
    sizeBytes: file.size,
    uploadedAt,
    kind: recognizeDocumentKind(fileName),
  };
};

const newId = (prefix: string) =>
  `${prefix}-${crypto.randomUUID().slice(0, 8)}`;

/** Finishes the fake processing of projects whose time is up */
const settleProcessing = () => {
  const now = Date.now();
  let changed = false;
  for (const [projectId, until] of Object.entries(db.processingUntil)) {
    if (until > now) continue;
    const project = db.projects.find((p) => p.id === projectId);
    if (project?.status === "processing") {
      for (const template of analysisTemplates) {
        db.analyses.push({
          ...structuredClone(template),
          id: newId("an"),
          projectId,
          generatedAt: new Date(until).toISOString(),
        });
      }
      project.status = "ready";
    }
    delete db.processingUntil[projectId];
    changed = true;
  }
  if (changed) persist();
};

const delay = async (ms = LATENCY_MS) => {
  await new Promise<void>((resolve) => setTimeout(resolve, ms));
  settleProcessing();
};

// ---------------------------------------------------------------------------
// Data access: stored projects take precedence over generated ones
// ---------------------------------------------------------------------------

const generatedById = () => new Map(generatedProjects().map((g) => [g.project.id, g]));

const allProjects = (): Project[] => {
  const stored = new Map(db.projects.map((p) => [p.id, p]));
  const generated = generatedProjects()
    .map((g) => g.project)
    .filter((p) => !stored.has(p.id));
  return [...db.projects, ...generated];
};

const findProject = (projectId: string): Project => {
  const project =
    db.projects.find((p) => p.id === projectId) ??
    generatedById().get(projectId)?.project;
  if (!project) throw new NotFoundError("Projeto");
  return project;
};

/** Copy-on-write: a generated project that changes is stored from then on */
const storedProject = (projectId: string): Project => {
  const stored = db.projects.find((p) => p.id === projectId);
  if (stored) return stored;
  const copy = structuredClone(findProject(projectId));
  db.projects.push(copy);
  return copy;
};

/** A project of the static export enters the mock db on first write (spec 14 E1):
 *  mutations stay on the mock path; reads never mix the two sources. */
export const adoptStaticProject = async (projectId: string): Promise<boolean> => {
  if (db.projects.some((p) => p.id === projectId)) return true;
  const exported = await staticGetProject(projectId);
  if (!exported) return false;
  db.projects.push(structuredClone(exported));
  return true;
};

/** Contestations as stored, with defaults for records saved before "status" existed */
const contestationsOf = (projectId: string): Contestation[] =>
  db.contestations
    .filter((c) => c.projectId === projectId)
    .map((c) => ({ ...c, status: c.status ?? "open" }));

/** Analyses as the analyst sees them: with accepted contestations applied */
const analysesOf = (projectId: string): Analysis[] => {
  const stored = db.analyses.filter((a) => a.projectId === projectId);
  const generated = generatedById().get(projectId);
  const base = stored.length ? stored : generated ? synthesizeAnalyses(generated) : [];
  const contestations = contestationsOf(projectId);
  return sortByFramework(base.map((a) => applyAdjustments(a, contestations)));
};

const decisionsOf = (projectId: string): Decision[] => {
  const generated = generatedById().get(projectId)?.decision;
  return [
    ...(generated ? [generated] : []),
    ...db.decisions.filter((d) => d.projectId === projectId),
  ].sort((a, b) => a.decidedAt.localeCompare(b.decidedAt));
};

/** Cheap summary for generated projects: scores without building the trees */
const generatedScoreSummary = (g: GeneratedProject) =>
  g.project.status === "ready" || g.project.status === "decided"
    ? analysisTemplates[0].criteria.map((c, i) => ({
        criterionKey: c.key,
        name: c.name,
        score: g.scores[0][i],
      }))
    : undefined;

const toSummary = (project: Project, generated?: GeneratedProject): ProjectSummary => {
  const contestations = contestationsOf(project.id);
  const stored = db.analyses.filter((a) => a.projectId === project.id);
  // Full (adjusted) analyses only when needed: stored ones, or accepted contestations
  const needsFull =
    stored.length > 0 || contestations.some((c) => c.resolution?.verdict === "accepted");
  const primary = needsFull ? analysesOf(project.id)[0] : undefined;
  const decisions = decisionsOf(project.id);
  const last = decisions.at(-1);
  return {
    ...project,
    frameworks: needsFull
      ? analysesOf(project.id).map((a) => a.framework)
      : generated && generatedScoreSummary(generated)
        ? analysisTemplates.map((t) => t.framework)
        : [],
    scoreSummary: primary
      ? primary.criteria.map((c) => ({ criterionKey: c.key, name: c.name, score: c.score }))
      : generated && generatedScoreSummary(generated),
    lastDecision: last && {
      outcome: last.outcome,
      decidedAt: last.decidedAt,
      analystName: last.analystName,
    },
    contestationCount: contestations.length,
    openContestationCount: contestations.filter((c) => c.status === "open").length,
    decidedCriteria: decidedCriteriaOf(project, primary, generated),
    processingProgress: project.status === "processing" ? processingProgressOf(project) : undefined,
  };
};

/** Criteria of the primary method with every rule rated by the analyst */
const decidedCriteriaOf = (
  project: Project,
  primary: Analysis | undefined,
  generated: GeneratedProject | undefined,
): ProjectSummary["decidedCriteria"] => {
  if (project.status !== "ready" && project.status !== "decided") return undefined;
  // Generated projects share the template's structure: no need to build the tree
  const analysis =
    primary ??
    db.analyses.find((a) => a.projectId === project.id) ??
    (generated ? { ...analysisTemplates[0], id: `an-${project.id}-0` } : undefined);
  if (!analysis) return undefined;
  const ratings = db.ruleDecisions.filter((d) => d.projectId === project.id);
  return { decided: decidedCriteriaCount(analysis, ratings), total: analysis.criteria.length };
};

/** MOCK: uploads finish after MOCK_PROCESSING_MS; generated ones never do (stable %) */
const processingProgressOf = (project: Project) => {
  const until = db.processingUntil[project.id];
  if (until) return Math.min(0.95, Math.max(0.05, 1 - (until - Date.now()) / MOCK_PROCESSING_MS));
  return 0.15 + ((Math.abs(hashId(project.id)) % 70) / 100);
};

// ---------------------------------------------------------------------------
// Auth (MOCK: any password; the user must exist)
// ---------------------------------------------------------------------------

export const listDemoUsers = async (): Promise<User[]> => {
  await delay(150);
  if (dataSource() === "static") {
    const exported = await staticUsers();
    if (exported && exported.length > 0) return structuredClone(exported);
  }
  if (dataSource() === "api") {
    try {
      return await apiJson<User[]>("/users"); // the seeded analysts (any password in the demo)
    } catch {
      /* fall back to the mocks below */
    }
  }
  return structuredClone(mockUsers);
};

const allUsers = () => [...mockUsers, ...db.users];

const sameEmail = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

export const login = async (email: string, password: string): Promise<User> => {
  if (dataSource() === "api") {
    try {
      const tokens = await apiPost<{ access_token: string; refresh_token: string }>("/auth/login", {
        email,
        password,
      });
      saveTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      return { id: "", name: email.split("@")[0], email }; // id resolved by /users/me on session restore
    } catch {
      throw new AuthError();
    }
  }
  await delay();
  if (dataSource() === "static") {
    const exported = await staticUsers();
    const user = exported?.find((u) => sameEmail(u.email, email));
    if (!user || !password) throw new AuthError();
    return structuredClone(user);
  }
  const user = allUsers().find((u) => sameEmail(u.email, email));
  if (!user || !password) throw new AuthError();
  return structuredClone(user);
};

/** MOCK sign-up: creates the analyst (with no projects) and signs in; any password works */
export const registerUser = async (name: string, email: string, password: string): Promise<User> => {
  await delay();
  if (!name.trim() || !email.trim() || !password) throw new AuthError("Preencha nome, e-mail e senha");
  if (allUsers().some((u) => sameEmail(u.email, email))) {
    throw new AuthError("Já existe uma conta com este e-mail");
  }
  const user: User = { id: newId("u"), name: name.trim(), email: email.trim().toLowerCase() };
  db.users.push(user);
  persist();
  return structuredClone(user);
};

export const getUser = async (userId: string): Promise<User> => {
  await delay(100);
  if (dataSource() === "static") {
    const exported = await staticUsers();
    const user = exported?.find((u) => u.id === userId);
    if (!user) throw new AuthError("Sessão expirada");
    return structuredClone(user);
  }
  const user = allUsers().find((u) => u.id === userId);
  if (!user) throw new AuthError("Sessão expirada");
  return structuredClone(user);
};

// ---------------------------------------------------------------------------
// Projects, analyses, decisions, contestations
// ---------------------------------------------------------------------------

/** One page of the analyst's projects, with filters (server-side in the real API) */
export const listProjects = async (query: ProjectQuery): Promise<ProjectPage> => {
  if (dataSource() === "static") return staticListProjects(query);
  if (dataSource() === "api") {
    try {
      const params = new URLSearchParams({ sort: query.sort, page: String(query.page), pageSize: String(query.pageSize) });
      if (query.ownerId) params.set("ownerId", query.ownerId);
      if (query.search) params.set("search", query.search);
      return await apiJson<ProjectPage>(`/projects?${params}`);
    } catch {
      /* the back-end being down must never break the demo */
    }
  }
  await delay();
  const generated = generatedById();
  const summaries = allProjects().map((p) => toSummary(p, generated.get(p.id)));
  return structuredClone(applyProjectQuery(summaries, query));
};

export const getProject = async (projectId: string): Promise<Project> => {
  if (dataSource() === "static") {
    const exported = await staticGetProject(projectId);
    if (exported) return exported;
  }
  if (dataSource() === "api") {
    try {
      return await apiJson<Project>(`/projects/${projectId}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) throw new NotFoundError("Projeto");
      /* fall back to the mock */
    }
  }
  await delay();
  return structuredClone(findProject(projectId));
};

export const createProject = async (
  input: NewProjectInput,
  ownerId: string,
): Promise<Project> => {
  if (dataSource() === "api") {
    try {
      const form = new FormData();
      form.set("name", input.name.trim());
      if (input.company) form.set("company", input.company.trim());
      if (input.freeText) form.set("freeText", input.freeText.trim());
      for (const file of input.files) form.append("files", file, file.name);
      return await apiPostForm<Project>("/projects", form); // 201 + the created project; the analysis starts in the background
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  const now = new Date().toISOString();
  const project: Project = {
    id: newId("p"),
    ownerId,
    name: input.name.trim(),
    company: input.company?.trim() || undefined,
    freeText: input.freeText?.trim() || undefined,
    createdAt: now,
    status: "processing",
    webSearch: input.webSearch,
    // Mock: keep only file metadata, nothing is uploaded
    documents: input.files.map((file) => toDocument(file, now)),
  };
  db.projects.push(project);
  db.processingUntil[project.id] = Date.now() + MOCK_PROCESSING_MS;
  persist();

  return structuredClone(project);
};

/**
 * Replaces the file that could not be read and processes the project again.
 * MOCK: like a new upload, the analysis is ready after MOCK_PROCESSING_MS.
 */
export const resendDocument = async (projectId: string, file: File): Promise<Project> => {
  await delay();
  const project = storedProject(projectId);
  if (project.status !== "error") throw new Error("O projeto não está aguardando reenvio.");
  const now = new Date().toISOString();
  const failed = project.readError?.fileName;
  project.documents = [
    ...project.documents.filter((doc) => doc.fileName !== failed),
    toDocument(file, now),
  ];
  project.readError = undefined;
  project.status = "processing";
  db.processingUntil[project.id] = Date.now() + MOCK_PROCESSING_MS;
  persist();
  return structuredClone(project);
};

/**
 * Every analysis of a project, one per method, in FRAMEWORK_ORDER.
 * Resolves to null while the project is still being processed.
 */
export const getAnalyses = async (projectId: string): Promise<Analysis[] | null> => {
  if (dataSource() === "static") {
    const exported = await staticGetAnalyses(projectId);
    if (exported !== null) return exported;
    const exists = await staticGetProject(projectId);
    if (exists) return null; // project in the export without a finished analysis
  }
  if (dataSource() === "api") {
    try {
      return await apiJson<Analysis[] | null>(`/projects/${projectId}/analyses`);
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  findProject(projectId);
  const analyses = analysesOf(projectId);
  // Mock: the real back-end will send scoreExplanation itself
  return analyses.length > 0
    ? analyses.map((a) => withScoreExplanations(structuredClone(a)))
    : null;
};

/** Decision trail, oldest first. Every save adds a new entry (never edits). */
export const listDecisions = async (projectId: string): Promise<Decision[]> => {
  if (dataSource() === "static") return staticDecisions(projectId);
  if (dataSource() === "api") {
    try {
      return await apiJson<Decision[]>(`/projects/${projectId}/decisions`);
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  return structuredClone(decisionsOf(projectId));
};

// ---------------------------------------------------------------------------
// Writes (E3): real API first, mock as the never-failing fallback
// ---------------------------------------------------------------------------

/** The front has 3 outcomes; the back-end's decision trail has 4 (the class vocabulary). */
const OUTCOME_TO_API: Record<string, string> = {
  eligible: "eligible",
  needs_review: "insufficient_evidence",
  not_eligible: "not_eligible",
};
const OUTCOME_FROM_API: Record<string, string> = {
  eligible: "eligible",
  eligible_with_caveats: "eligible",
  insufficient_evidence: "needs_review",
  not_eligible: "not_eligible",
};

export const saveDecision = async (
  input: NewDecisionInput,
): Promise<Decision> => {
  if (dataSource() === "api") {
    try {
      const saved = await apiPost<Decision & { outcome: string }>(
        `/projects/${input.projectId}/decisions`,
        { ...input, outcome: OUTCOME_TO_API[input.outcome] ?? input.outcome },
      );
      return { ...saved, outcome: (OUTCOME_FROM_API[saved.outcome] ?? saved.outcome) as Decision["outcome"] };
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  if (dataSource() === "static") await adoptStaticProject(input.projectId);
  const project = storedProject(input.projectId);
  const decision: Decision = { ...input, decidedAt: new Date().toISOString() };
  db.decisions.push(decision);
  project.status = "decided";
  persist();
  return structuredClone(decision);
};

export interface ExportedFile {
  fileName: string;
  content: Blob;
}

/**
 * Decision of one method as a spreadsheet (CSV). Back-end:
 * GET /analyses/{analysisId}/report.csv, file name from Content-Disposition.
 */
export const exportDecisionCsv = async (projectId: string, analysisId: string): Promise<ExportedFile> => {
  await delay();
  const project = findProject(projectId);
  const stored = analysesOf(projectId).find((a) => a.id === analysisId);
  if (!stored) throw new NotFoundError("Análise");
  const analysis = withScoreExplanations(structuredClone(stored));
  const pendencies = pendenciesOf(analysis, project, contestationsOf(projectId));
  const csv = toCsv(decisionCsvColumns(analysis.criteria.length), [
    decisionCsvRow(project, analysis, decisionsOf(projectId).at(-1), pendencies),
  ]);
  return {
    fileName: decisionCsvFileName(project, analysis),
    content: new Blob([csv], { type: "text/csv;charset=utf-8" }),
  };
};

/** Contestations of a project, oldest first. Append-only, like decisions. */
export const listContestations = async (projectId: string): Promise<Contestation[]> => {
  if (dataSource() === "static") return staticContestations(projectId);
  await delay();
  return structuredClone(
    contestationsOf(projectId).sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  );
};

export const createContestation = async (
  input: NewContestationInput,
): Promise<Contestation> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<Contestation>(`/projects/${input.projectId}/contestations`, input);
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  if (dataSource() === "static") await adoptStaticProject(input.projectId);
  findProject(input.projectId);
  const contestation: Contestation = {
    ...input,
    id: newId("ct"),
    status: "open",
    createdAt: new Date().toISOString(),
  };
  db.contestations.push(contestation);
  persist();
  return structuredClone(contestation);
};

/**
 * Asks the model to reanalyse a contestation. MOCK: see src/mocks/reanalysis.ts.
 * The contestation becomes "resolved" (accepted or maintained); accepted
 * changes show up in the analysis from then on.
 */
export const requestReanalysis = async (contestationId: string): Promise<Contestation> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<Contestation>(`/contestations/${contestationId}/reanalysis`, {});
    } catch {
      /* fall back to the mock */
    }
  }
  await delay(REANALYSIS_LATENCY_MS);
  const stored = db.contestations.find((c) => c.id === contestationId);
  if (!stored) throw new NotFoundError("Contestação");
  const current = { ...stored, status: stored.status ?? "open" };
  if (current.status === "resolved") return structuredClone(current);

  const analysis = analysesOf(current.projectId).find((a) => a.id === current.analysisId);
  if (!analysis) throw new NotFoundError("Análise");
  stored.status = "resolved";
  stored.resolution = reanalyze(analysis, current, new Date().toISOString());
  persist();
  return structuredClone(stored);
};

/** Analyst's rule ratings, oldest first. Append-only: the latest per rule is the current one. */
export const listRuleDecisions = async (projectId: string): Promise<RuleDecision[]> => {
  if (dataSource() === "static") return staticRuleDecisions(projectId);
  await delay();
  return structuredClone(db.ruleDecisions.filter((d) => d.projectId === projectId));
};

export const createRuleDecision = async (input: NewRuleDecisionInput): Promise<RuleDecision> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<RuleDecision>(`/projects/${input.projectId}/rule-decisions`, input);
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  findProject(input.projectId);
  const decision: RuleDecision = { ...input, id: newId("rd"), createdAt: new Date().toISOString() };
  db.ruleDecisions.push(decision);
  persist();
  return structuredClone(decision);
};

/** Evidences confirmed or discarded by the analyst, oldest first. Append-only. */
export const listEvidenceReviews = async (projectId: string): Promise<EvidenceReview[]> => {
  if (dataSource() === "static") return staticEvidenceReviews(projectId);
  await delay();
  return structuredClone(db.evidenceReviews.filter((r) => r.projectId === projectId));
};

export const createEvidenceReview = async (
  input: NewEvidenceReviewInput,
): Promise<EvidenceReview> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<EvidenceReview>(`/projects/${input.projectId}/evidence-reviews`, input);
    } catch {
      /* fall back to the mock */
    }
  }
  await delay();
  findProject(input.projectId);
  const review: EvidenceReview = { ...input, id: newId("er"), createdAt: new Date().toISOString() };
  db.evidenceReviews.push(review);
  persist();
  return structuredClone(review);
};

// ---------------------------------------------------------------------------
// Assistant
// ---------------------------------------------------------------------------

/**
 * Analysis assistant (chatbot). MOCK: rule-based answers from the analysis on
 * screen. To integrate, send `question` + `context` to the ai-microservice and
 * keep the same AssistantAnswer shape (blocks + sources + suggestions).
 */
export const askAssistant = async (
  question: string,
  context: AssistantContext,
): Promise<AssistantAnswer> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<AssistantAnswer>("/assistant/ask", {
        question,
        context: {
          screen: context.screen,
          analysis: { id: context.analysis?.id },
          selectedNodeId: context.selectedNodeId,
          debateNodeId: context.debateNodeId ?? null,
        },
      });
    } catch {
      /* fall back to the mock */
    }
  }
  await delay(ASSISTANT_LATENCY_MS);
  return context.debateNodeId
    ? debateReply(question, context)
    : answerQuestion(question, context);
};

/** Opens a debate about one node: the model states the basis of its reading */
export const openDebate = async (
  nodeId: string,
  context: AssistantContext,
): Promise<AssistantAnswer> => {
  if (dataSource() === "api") {
    try {
      return await apiPost<AssistantAnswer>("/assistant/debate", {
        nodeId,
        context: {
          screen: context.screen,
          analysis: { id: context.analysis?.id },
          selectedNodeId: context.selectedNodeId,
        },
      });
    } catch {
      /* fall back to the mock */
    }
  }
  await delay(ASSISTANT_LATENCY_MS);
  return debateOpening({ ...context, debateNodeId: nodeId }, nodeId);
};
