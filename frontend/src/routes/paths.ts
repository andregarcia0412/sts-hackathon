import type { Framework } from "@/domain/types";

export const SELECTED_NODE_PARAM = "no";
export const FRAMEWORK_PARAM = "metodo";

const query = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => !!entry[1]),
  ).toString();
  return search ? `?${search}` : "";
};

export const paths = {
  projects: () => "/projetos",
  analysis: (projectId: string, nodeId?: string, framework?: Framework) =>
    `/projetos/${projectId}/analise${query({ [FRAMEWORK_PARAM]: framework, [SELECTED_NODE_PARAM]: nodeId })}`,
  decision: (projectId: string, framework?: Framework) =>
    `/projetos/${projectId}/decisao${query({ [FRAMEWORK_PARAM]: framework })}`,
};

/** Anchor of a node in the decision document; the method keeps different trees apart */
export const reportAnchorId = (analysis: { framework: Framework }, nodeId: string) =>
  `no-${analysis.framework}-${nodeId}`;
