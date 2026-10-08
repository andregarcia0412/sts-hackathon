import type {
  Analysis,
  Decision,
  NewDecisionInput,
  NewProjectInput,
  Project,
  ProjectSummary,
} from "@/domain/types";
import type { AssistantAnswer, AssistantContext } from "@/domain/assistant";
import { answerQuestion } from "@/mocks/assistantEngine";
import { withScoreExplanations } from "@/mocks/scoreExplanations";
import {
  analysisTemplate,
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

/*
 * Mock database, persisted in localStorage so a demo survives a page reload.
 * Call resetMockData() (e.g. from the console via window.resetMockData) to
 * start over from the fictitious examples.
 */
// Bump the version when src/mocks changes, or browsers keep the old copy
const STORAGE_KEY = "lei-do-bem:mock-db:v1";

interface MockDb {
  projects: Project[];
  analyses: Analysis[];
  decisions: Decision[];
  /** Mock-created projects become "ready" after this timestamp (ms) */
  processingUntil: Record<string, number>;
}

const seedDb = (): MockDb => ({
  projects: structuredClone(mockProjects),
  analyses: structuredClone(mockAnalyses),
  decisions: structuredClone(mockDecisions),
  processingUntil: {},
});

const loadDb = (): MockDb => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as MockDb;
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

/** Finishes the fake processing of projects whose time is up */
const settleProcessing = () => {
  const now = Date.now();
  let changed = false;
  for (const [projectId, until] of Object.entries(db.processingUntil)) {
    if (until > now) continue;
    const project = db.projects.find((p) => p.id === projectId);
    if (project?.status === "processing") {
      db.analyses.push({
        ...structuredClone(analysisTemplate),
        id: newId("an"),
        projectId,
        generatedAt: new Date(until).toISOString(),
      });
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

const newId = (prefix: string) =>
  `${prefix}-${crypto.randomUUID().slice(0, 8)}`;

const toSummary = (project: Project): ProjectSummary => {
  const analysis = db.analyses.find((a) => a.projectId === project.id);
  return {
    ...project,
    scoreSummary: analysis?.criteria.map((c) => ({
      criterionKey: c.key,
      name: c.name,
      score: c.score,
    })),
  };
};

const findProject = (projectId: string) => {
  const project = db.projects.find((p) => p.id === projectId);
  if (!project) throw new NotFoundError("Projeto");
  return project;
};

export const listProjects = async (): Promise<ProjectSummary[]> => {
  await delay();
  return structuredClone(
    [...db.projects]
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .map(toSummary),
  );
};

export const getProject = async (projectId: string): Promise<Project> => {
  await delay();
  return structuredClone(findProject(projectId));
};

export const createProject = async (
  input: NewProjectInput,
): Promise<Project> => {
  await delay();
  const now = new Date().toISOString();
  const project: Project = {
    id: newId("p"),
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

/** Resolves to null while the project is still being processed */
export const getAnalysis = async (
  projectId: string,
): Promise<Analysis | null> => {
  await delay();
  findProject(projectId);
  const analysis = db.analyses.find((a) => a.projectId === projectId);
  // Mock: the real back-end will send scoreExplanation itself
  return analysis ? withScoreExplanations(structuredClone(analysis)) : null;
};

/** Decision trail, oldest first. Every save adds a new entry (never edits). */
export const listDecisions = async (projectId: string): Promise<Decision[]> => {
  await delay();
  return structuredClone(
    db.decisions
      .filter((d) => d.projectId === projectId)
      .sort((a, b) => a.decidedAt.localeCompare(b.decidedAt)),
  );
};

export const saveDecision = async (
  input: NewDecisionInput,
): Promise<Decision> => {
  await delay();
  const project = findProject(input.projectId);
  const decision: Decision = { ...input, decidedAt: new Date().toISOString() };
  db.decisions.push(decision);
  project.status = "decided";
  persist();
  return structuredClone(decision);
};

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
  return answerQuestion(question, context);
};
