import type { Framework } from "@/domain/types";

export const SELECTED_NODE_PARAM = "no";
export const FRAMEWORK_PARAM = "metodo";
/** Opens the "Novo projeto" (upload) dialog on the projects page */
export const NEW_PROJECT_PARAM = "novo";

const query = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => !!entry[1]),
  ).toString();
  return search ? `?${search}` : "";
};

export const paths = {
  projects: () => "/projetos",
  /** "Upload de arquivos" step: the new project screen */
  newProject: () => "/projetos/novo",
  analysis: (projectId: string, nodeId?: string, framework?: Framework) =>
    `/projetos/${projectId}/analise${query({ [FRAMEWORK_PARAM]: framework, [SELECTED_NODE_PARAM]: nodeId })}`,
  /** `nodeId` opens that criterion / rule in the document */
  decision: (projectId: string, framework?: Framework, nodeId?: string) =>
    `/projetos/${projectId}/decisao${query({ [FRAMEWORK_PARAM]: framework, [SELECTED_NODE_PARAM]: nodeId })}`,
};

/** Anchor of a node in the decision document; the method keeps different trees apart */
export const reportAnchorId = (analysis: { framework: Framework }, nodeId: string) =>
  `no-${analysis.framework}-${nodeId}`;
