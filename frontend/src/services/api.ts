import type {
  Analysis,
  Decision,
  NewDecisionInput,
  NewProjectInput,
  Project,
  ProjectSummary,
} from "@/domain/types";
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

export class NotFoundError extends Error {
  constructor(what: string) {
    super(`${what} não encontrado(a)`);
    this.name = "NotFoundError";
  }
}

const db = {
  projects: structuredClone(mockProjects),
  analyses: structuredClone(mockAnalyses),
  decisions: structuredClone(mockDecisions),
};

const delay = (ms = LATENCY_MS) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

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

  setTimeout(() => {
    db.analyses.push({
      ...structuredClone(analysisTemplate),
      id: newId("an"),
      projectId: project.id,
      generatedAt: new Date().toISOString(),
    });
    project.status = "ready";
  }, MOCK_PROCESSING_MS);

  return structuredClone(project);
};

/** Resolves to null while the project is still being processed */
export const getAnalysis = async (
  projectId: string,
): Promise<Analysis | null> => {
  await delay();
  findProject(projectId);
  const analysis = db.analyses.find((a) => a.projectId === projectId);
  return analysis ? structuredClone(analysis) : null;
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
  return structuredClone(decision);
};
