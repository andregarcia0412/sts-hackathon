import type {
  Analysis,
  Contestation,
  NewContestationInput,
  Decision,
  NewDecisionInput,
  NewProjectInput,
  Project,
  ProjectPage,
  ProjectQuery,
  ProjectSummary,
  User,
} from "@/domain/types";
import type { AssistantAnswer, AssistantContext } from "@/domain/assistant";
import { answerQuestion } from "@/mocks/assistantEngine";
import { debateOpening, debateReply } from "@/mocks/debateEngine";
import { generatedProjects, synthesizeAnalyses } from "@/mocks/generatedProjects";
import type { GeneratedProject } from "@/mocks/generatedProjects";
import { applyProjectQuery } from "@/mocks/projectQuery";
import { withScoreExplanations } from "@/mocks/scoreExplanations";
import { mockUsers } from "@/mocks/users";
import { sortByFramework } from "@/domain/frameworks";
import {
  analysisTemplates,
  mockAnalyses,
  mockDecisions,
  mockProjects,
} from "@/mocks/projects";

/*
 * Service layer. Screens only talk to these functions.
 * For now everything is read from in-memory mocks with an artificial delay;
 * when the back-end exists, swap the bodies for fetch calls here.
 */

const LATENCY_MS = 400;
const MOCK_PROCESSING_MS = 5000;
const ASSISTANT_LATENCY_MS = 700;

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
const STORAGE_KEY = "lei-do-bem:mock-db:v4";

interface MockDb {
  projects: Project[];
  analyses: Analysis[];
  decisions: Decision[];
  contestations: Contestation[];
  /** Mock-created projects become "ready" after this timestamp (ms) */
  processingUntil: Record<string, number>;
}

const seedDb = (): MockDb => ({
  projects: structuredClone(mockProjects),
  analyses: structuredClone(mockAnalyses),
  decisions: structuredClone(mockDecisions),
  contestations: [],
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

const analysesOf = (projectId: string): Analysis[] => {
  const stored = db.analyses.filter((a) => a.projectId === projectId);
  if (stored.length) return sortByFramework(stored);
  const generated = generatedById().get(projectId);
  return generated ? sortByFramework(synthesizeAnalyses(generated)) : [];
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
  const stored = db.analyses.filter((a) => a.projectId === project.id);
  const primary = sortByFramework(stored)[0];
  const decisions = decisionsOf(project.id);
  const last = decisions.at(-1);
  return {
    ...project,
    frameworks: stored.length
      ? sortByFramework(stored).map((a) => a.framework)
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
    contestationCount: db.contestations.filter((c) => c.projectId === project.id).length,
  };
};

// ---------------------------------------------------------------------------
// Auth (MOCK: any password; the user must exist)
// ---------------------------------------------------------------------------

export const listDemoUsers = async (): Promise<User[]> => {
  await delay(150);
  return structuredClone(mockUsers);
};

export const login = async (email: string, password: string): Promise<User> => {
  await delay();
  const user = mockUsers.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
  if (!user || !password) throw new AuthError();
  return structuredClone(user);
};

export const getUser = async (userId: string): Promise<User> => {
  await delay(100);
  const user = mockUsers.find((u) => u.id === userId);
  if (!user) throw new AuthError("Sessão expirada");
  return structuredClone(user);
};

// ---------------------------------------------------------------------------
// Projects, analyses, decisions, contestations
// ---------------------------------------------------------------------------

/** One page of the analyst's projects, with filters (server-side in the real API) */
export const listProjects = async (query: ProjectQuery): Promise<ProjectPage> => {
  await delay();
  const generated = generatedById();
  const summaries = allProjects().map((p) => toSummary(p, generated.get(p.id)));
  return structuredClone(applyProjectQuery(summaries, query));
};

export const getProject = async (projectId: string): Promise<Project> => {
  await delay();
  return structuredClone(findProject(projectId));
};

export const createProject = async (
  input: NewProjectInput,
  ownerId: string,
): Promise<Project> => {
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
    // Mock: keep only file metadata, nothing is uploaded
    documents: input.files.map((file) => ({
      id: newId("doc"),
      fileName: file.name,
      mimeType: file.type,
      sizeBytes: file.size,
      uploadedAt: now,
    })),
  };
  db.projects.push(project);
  db.processingUntil[project.id] = Date.now() + MOCK_PROCESSING_MS;
  persist();

  return structuredClone(project);
};

/**
 * Every analysis of a project, one per method, in FRAMEWORK_ORDER.
 * Resolves to null while the project is still being processed.
 */
export const getAnalyses = async (projectId: string): Promise<Analysis[] | null> => {
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
  await delay();
  return structuredClone(decisionsOf(projectId));
};

export const saveDecision = async (
  input: NewDecisionInput,
): Promise<Decision> => {
  await delay();
  const project = storedProject(input.projectId);
  const decision: Decision = { ...input, decidedAt: new Date().toISOString() };
  db.decisions.push(decision);
  project.status = "decided";
  persist();
  return structuredClone(decision);
};

/** Contestations of a project, oldest first. Append-only, like decisions. */
export const listContestations = async (projectId: string): Promise<Contestation[]> => {
  await delay();
  return structuredClone(
    db.contestations
      .filter((c) => c.projectId === projectId)
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  );
};

export const createContestation = async (
  input: NewContestationInput,
): Promise<Contestation> => {
  await delay();
  findProject(input.projectId);
  const contestation: Contestation = {
    ...input,
    id: newId("ct"),
    createdAt: new Date().toISOString(),
  };
  db.contestations.push(contestation);
  persist();
  return structuredClone(contestation);
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
  await delay(ASSISTANT_LATENCY_MS);
  return debateOpening({ ...context, debateNodeId: nodeId }, nodeId);
};
